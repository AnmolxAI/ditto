"""
Linear API client with strict field validation.
Only validates and creates issues with explicitly provided, validated data.
"""

import requests
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from dateutil import parser as date_parser


class LinearClient:
    """Client for Linear GraphQL API with field validation."""
    
    def __init__(self, api_key: str, api_url: str = "https://api.linear.app/graphql"):
        self.api_key = api_key
        self.api_url = api_url
        # Linear API keys should be used directly without Bearer prefix
        # Remove Bearer prefix if present
        auth_key = api_key.replace("Bearer ", "").strip()
        self.headers = {
            "Authorization": auth_key,
            "Content-Type": "application/json"
        }
        self._cache = {
            "teams": {},
            "projects": {},
            "cycles": {},
            "users": {},
            "labels": {},
            "priorities": {}
        }
    
    def _query(self, query: str, variables: Optional[Dict] = None) -> Dict:
        """Execute a GraphQL query."""
        payload = {"query": query, "variables": variables or {}}
        response = requests.post(self.api_url, json=payload, headers=self.headers)
        
        # Get response JSON before raising for status
        try:
            result = response.json()
        except:
            result = {}
        
        # Check for GraphQL errors in response
        if result.get("errors"):
            error_messages = [err.get("message", str(err)) for err in result.get("errors", [])]
            raise Exception(f"GraphQL Error: {'; '.join(error_messages)}")
        
        # Raise for HTTP errors
        response.raise_for_status()
        return result
    
    def _load_teams(self) -> Dict[str, Dict]:
        """Load all teams and cache them."""
        query = """
        query {
            teams {
                nodes {
                    id
                    key
                    name
                }
            }
        }
        """
        result = self._query(query)
        teams = {}
        for team in result.get("data", {}).get("teams", {}).get("nodes", []):
            teams[team["key"].lower()] = team
            teams[team["name"].lower()] = team
        self._cache["teams"] = teams
        return teams
    
    def _load_projects(self, team_id: Optional[str] = None) -> Dict[str, Dict]:
        """Load projects, optionally filtered by team."""
        query = """
        query($teamId: String) {
            projects(filter: { team: { id: { eq: $teamId } } }) {
                nodes {
                    id
                    name
                    key
                }
            }
        }
        """
        variables = {"teamId": team_id} if team_id else {}
        result = self._query(query, variables)
        projects = {}
        for project in result.get("data", {}).get("projects", {}).get("nodes", []):
            key = project.get("key", "").lower()
            name = project.get("name", "").lower()
            if key:
                projects[key] = project
            if name:
                projects[name] = project
        return projects
    
    def _load_cycles(self, team_id: str) -> Dict[str, Dict]:
        """Load active cycles for a team."""
        query = """
        query($teamId: String!) {
            cycles(filter: { team: { id: { eq: $teamId } }, isActive: { eq: true } }) {
                nodes {
                    id
                    name
                    number
                }
            }
        }
        """
        result = self._query(query, {"teamId": team_id})
        cycles = {}
        for cycle in result.get("data", {}).get("cycles", {}).get("nodes", []):
            name = cycle.get("name", "").lower()
            cycles[name] = cycle
            # Also index by number
            cycles[str(cycle.get("number", ""))] = cycle
        return cycles
    
    def _load_users(self) -> Dict[str, Dict]:
        """Load all users."""
        query = """
        query {
            users {
                nodes {
                    id
                    name
                    email
                }
            }
        }
        """
        result = self._query(query)
        users = {}
        for user in result.get("data", {}).get("users", {}).get("nodes", []):
            name = user.get("name", "").lower()
            email = user.get("email", "").lower()
            if name:
                users[name] = user
            if email:
                users[email] = user
        self._cache["users"] = users
        return users
    
    def _load_labels(self, team_id: Optional[str] = None) -> Dict[str, Dict]:
        """Load labels, optionally filtered by team."""
        query = """
        query($teamId: String) {
            issueLabels(filter: { team: { id: { eq: $teamId } } }) {
                nodes {
                    id
                    name
                }
            }
        }
        """
        variables = {"teamId": team_id} if team_id else {}
        result = self._query(query, variables)
        labels = {}
        for label in result.get("data", {}).get("issueLabels", {}).get("nodes", []):
            name = label.get("name", "").lower()
            labels[name] = label
        return labels
    
    def validate_team(self, team_value: str) -> Tuple[bool, Optional[Dict]]:
        """Validate team by name or key. Returns (is_valid, team_data)."""
        if not team_value:
            return False, None
        
        teams = self._load_teams()
        team_lower = team_value.lower().strip()
        team = teams.get(team_lower)
        
        if team:
            return True, team
        return False, None
    
    def validate_project(self, project_value: str, team_id: Optional[str] = None) -> Tuple[bool, Optional[Dict]]:
        """Validate project. Returns (is_valid, project_data)."""
        if not project_value:
            return False, None
        
        projects = self._load_projects(team_id)
        project_lower = project_value.lower().strip()
        project = projects.get(project_lower)
        
        if project:
            return True, project
        return False, None
    
    def validate_cycle(self, cycle_value: str, team_id: str) -> Tuple[bool, Optional[Dict]]:
        """Validate active cycle for team. Returns (is_valid, cycle_data)."""
        if not cycle_value or not team_id:
            return False, None
        
        cycles = self._load_cycles(team_id)
        cycle_lower = cycle_value.lower().strip()
        cycle = cycles.get(cycle_lower)
        
        # Try matching "sprint 24" format
        if not cycle and "sprint" in cycle_lower:
            sprint_num = cycle_lower.replace("sprint", "").strip()
            cycle = cycles.get(sprint_num)
        
        if cycle:
            return True, cycle
        return False, None
    
    def validate_priority(self, priority_value: str) -> Tuple[bool, Optional[str]]:
        """Validate priority. Returns (is_valid, priority_enum)."""
        if not priority_value:
            return False, None
        
        priority_lower = priority_value.lower().strip()
        valid_priorities = {
            "low": "low",
            "medium": "medium",
            "high": "high",
            "urgent": "urgent"
        }
        
        priority = valid_priorities.get(priority_lower)
        if priority:
            return True, priority
        return False, None
    
    def validate_assignee(self, assignee_value: str) -> Tuple[bool, Optional[Dict]]:
        """Validate assignee by name or email. Returns (is_valid, user_data)."""
        if not assignee_value:
            return False, None
        
        users = self._load_users()
        assignee_lower = assignee_value.lower().strip()
        user = users.get(assignee_lower)
        
        if user:
            return True, user
        return False, None
    
    def validate_labels(self, label_values: List[str], team_id: Optional[str] = None) -> List[Dict]:
        """Validate labels. Returns list of valid label dicts."""
        if not label_values:
            return []
        
        labels = self._load_labels(team_id)
        valid_labels = []
        
        for label_value in label_values:
            label_lower = label_value.lower().strip()
            label = labels.get(label_lower)
            if label:
                valid_labels.append(label)
        
        return valid_labels
    
    def parse_due_date(self, date_value: str) -> Optional[str]:
        """Parse spoken date into ISO format. Returns None if cannot parse."""
        if not date_value:
            return None
        
        try:
            # Try parsing common formats
            date_str = date_value.strip()
            
            # Handle "March 15", "March 15th"
            if "th" in date_str or "st" in date_str or "nd" in date_str or "rd" in date_str:
                date_str = date_str.replace("th", "").replace("st", "").replace("nd", "").replace("rd", "")
            
            # Try parsing with dateutil
            parsed_date = date_parser.parse(date_str, fuzzy=True, default=datetime.now())
            return parsed_date.date().isoformat()
        except Exception:
            return None
    
    def create_issue(
        self,
        team_id: str,
        title: str,
        description: Optional[str] = None,
        project_id: Optional[str] = None,
        cycle_id: Optional[str] = None,
        due_date: Optional[str] = None,
        priority: Optional[str] = None,
        assignee_id: Optional[str] = None,
        label_ids: Optional[List[str]] = None
    ) -> Dict:
        """Create a Linear issue with validated fields."""
        
        # Build mutation
        mutation = """
        mutation(
            $teamId: String!,
            $title: String!,
            $description: String,
            $projectId: String,
            $cycleId: String,
            $dueDate: TimelessDate,
            $priority: Int,
            $assigneeId: String,
            $labelIds: [String!]
        ) {
            issueCreate(
                input: {
                    teamId: $teamId
                    title: $title
                    description: $description
                    projectId: $projectId
                    cycleId: $cycleId
                    dueDate: $dueDate
                    priority: $priority
                    assigneeId: $assigneeId
                    labelIds: $labelIds
                }
            ) {
                success
                issue {
                    id
                    identifier
                    url
                    title
                }
            }
        }
        """
        
        # Map priority string to Linear priority number
        # Linear uses: 0=No priority, 1=Urgent, 2=High, 3=Medium, 4=Low
        priority_map = {
            "urgent": 1,
            "high": 2,
            "medium": 3,
            "low": 4
        }
        priority_num = priority_map.get(priority) if priority else None
        
        variables = {
            "teamId": team_id,
            "title": title,
            "description": description,
            "projectId": project_id,
            "cycleId": cycle_id,
            "dueDate": due_date,
            "priority": priority_num,
            "assigneeId": assignee_id,
            "labelIds": label_ids
        }
        
        # Remove None values
        variables = {k: v for k, v in variables.items() if v is not None}
        
        result = self._query(mutation, variables)
        
        if result.get("data", {}).get("issueCreate", {}).get("success"):
            return result["data"]["issueCreate"]["issue"]
        else:
            errors = result.get("errors", [])
            raise Exception(f"Failed to create issue: {errors}")

