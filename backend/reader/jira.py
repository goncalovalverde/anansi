from jira import JIRA
import dateutil.parser
import hashlib
import logging
import requests
from pandas import NaT, DataFrame

import reader.cache

logger = logging.getLogger(__name__)


def validate_auth_config(jira_config: dict) -> None:
    """Raise ValueError if required credentials for the chosen auth method are missing."""
    method = jira_config.get("auth_method", "basic")
    url = jira_config.get("url", "").strip()

    if not url:
        raise ValueError("Jira URL is required.")

    if method == "pat":
        if not jira_config.get("pat_token", "").strip():
            raise ValueError("PAT token is required when auth method is 'pat'.")

    elif method == "oauth":
        oauth = jira_config.get("oauth", {})
        missing = [k for k in ("token", "token_secret", "consumer_key", "key_cert_file")
                   if not oauth.get(k, "").strip()]
        if missing:
            raise ValueError(
                f"OAuth fields are required: {', '.join(missing)}."
            )

    else:  # basic
        missing = [k for k in ("username", "password")
                   if not jira_config.get(k, "").strip()]
        if missing:
            raise ValueError(
                f"Basic auth fields are required: {', '.join(missing)}."
            )


class Jira:
    def __init__(self, jira_config: dict, workflow: list[str], db_path: str):
        self.jira_config = jira_config
        self.workflow = workflow
        self.db_path = db_path

        config_hash = self._compute_cache_hash()
        self.cache = reader.cache.Cache(db_path, config_hash)

    def _compute_cache_hash(self) -> str:
        url = self.jira_config.get("url", "")
        jql_query = self.jira_config.get("jql_query", "")
        workflow = str(self.workflow)
        return hashlib.md5((url + jql_query + workflow).encode("utf-8")).hexdigest()

    def get_issue_data(self, issue, issue_data: dict) -> None:
        issue_data["Key"].append(issue.key)
        issue_data["Type"].append(issue.fields.issuetype.name)
        issue_data["Creator"].append(issue.fields.creator.displayName)
        issue_data["Summary"].append(issue.fields.summary)
        issue_data["Created"].append(
            dateutil.parser.parse(issue.fields.created).replace(tzinfo=None)
        )
        issue_data["Status"].append(issue.fields.status.name)

        story_points_field = self.jira_config.get("story_points_field")
        sp_value = None
        if story_points_field:
            sp_value = getattr(issue.fields, story_points_field, None)
            # Log first few issues to debug
            if issue.key in ("PNC-499", "PNC-498", "PNC-497"):
                import logging
                logger = logging.getLogger(__name__)
                logger.info(f"{issue.key}: {story_points_field}={sp_value} (type: {type(sp_value).__name__})")
        issue_data["Story Points"].append(sp_value)

        epic_link_field = self.jira_config.get("epic_link_field")
        epic_link = None

        if epic_link_field:
            val = getattr(issue.fields, epic_link_field, None)
            if val is not None:
                # Some Jira versions return a string key; others return an object.
                epic_link = val.key if hasattr(val, "key") else str(val)

        # Fallback: next-gen / team-managed projects expose the epic via parent.
        if not epic_link:
            parent = getattr(issue.fields, "parent", None)
            if parent and getattr(getattr(parent, "fields", None), "issuetype", None):
                if parent.fields.issuetype.name == "Epic":
                    epic_link = parent.key

        issue_data["Epic Link"].append(epic_link or "No Epic")

        history_item = {step: NaT for step in self.workflow}

        for history in issue.changelog.histories:
            for item in history.items:
                if item.field == "status":
                    history_item[item.toString] = dateutil.parser.parse(
                        history.created
                    ).replace(tzinfo=None)

        for workflow_step in self.workflow:
            issue_data[workflow_step].append(history_item[workflow_step])

    def get_issues(self, progress_callback=None) -> list:
        """Fetch issues using REST API directly to ensure all fields are returned."""
        jira_url = self.jira_config["url"].rstrip("/")
        jql = self.jira_config["jql_query"]
        
        # Build auth for REST call
        auth = None
        headers = {}
        if self.jira_config.get("auth_method") == "pat":
            headers["Authorization"] = f"Bearer {self.jira_config.get('pat_token', '')}"
        elif self.jira_config.get("username") and self.jira_config.get("password"):
            auth = (self.jira_config["username"], self.jira_config["password"])
        
        issues = []
        i = 0
        chunk_size = 100
        
        while True:
            url = f"{jira_url}/rest/api/2/search"
            params = {
                "jql": jql,
                "startAt": i,
                "maxResults": chunk_size,
                "expand": "changelog",
                "fields": "*all",
            }
            
            try:
                resp = requests.get(url, params=params, headers=headers, auth=auth, timeout=30, verify=False)
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                logger.error(f"REST API call failed: {e}. Falling back to python-jira.")
                # Fallback to python-jira library
                jira = self.get_jira_instance()
                chunk = jira.search_issues(
                    jql, expand="changelog", maxResults=chunk_size, startAt=i
                )
                issues += list(chunk.iterable)
                if i >= chunk.total:
                    break
                i += chunk_size
                continue
            
            # Wrap REST response as issue-like objects for get_issue_data()
            for issue_dict in data.get("issues", []):
                issue = self._wrap_issue(issue_dict)
                issues.append(issue)
            
            if progress_callback:
                progress_callback(len(issues), data.get("total", chunk_size))
            
            if i + chunk_size >= data.get("total", 0):
                break
            i += chunk_size
        
        return issues
    
    @staticmethod
    def _wrap_issue(issue_dict: dict):
        """Convert REST API issue dict to object with .key, .fields, .changelog attributes."""
        class FieldsWrapper:
            def __init__(self, fields_dict):
                for key, val in fields_dict.items():
                    if isinstance(val, dict) and ("name" in val or "displayName" in val):
                        # Create object for nested structures like issuetype, creator, status
                        setattr(self, key, type('obj', (), val)())
                    else:
                        setattr(self, key, val)
        
        class HistoryWrapper:
            def __init__(self, histories):
                self.histories = histories
        
        class IssueWrapper:
            def __init__(self):
                self.key = issue_dict["key"]
                self.fields = FieldsWrapper(issue_dict.get("fields", {}))
                changelog_data = issue_dict.get("changelog", {})
                self.changelog = HistoryWrapper(changelog_data.get("histories", []))
        
        return IssueWrapper()

    def get_jira_data(self, progress_callback=None) -> DataFrame:
        if self.jira_config.get("cache") and self.cache.is_valid():
            logger.debug("Returning Jira data from cache")
            return self.cache.read()

        logger.debug("Fetching Jira data from API")
        issue_data: dict = {
            "Key": [],
            "Type": [],
            "Summary": [],
            "Creator": [],
            "Story Points": [],
            "Epic Link": [],
            "Status": [],
            "Created": [],
        }
        for workflow_step in self.workflow:
            issue_data[workflow_step] = []

        for issue in self.get_issues(progress_callback=progress_callback):
            self.get_issue_data(issue, issue_data)

        df = DataFrame(issue_data)
        df.fillna(NaT)
        return df

    def get_jira_instance(self) -> JIRA:
        jira_url = self.jira_config["url"]
        logger.debug("Connecting to Jira: %s", jira_url)

        validate_auth_config(self.jira_config)
        auth_method = self.jira_config.get("auth_method", "basic")
        api_version = str(self.jira_config.get("api_version", "2"))
        options = {"rest_api_version": api_version}
        logger.debug("Using Jira REST API v%s", api_version)

        if auth_method == "pat":
            logger.debug("Using PAT authentication")
            return JIRA(jira_url, token_auth=self.jira_config["pat_token"],
                        options=options)

        if auth_method == "oauth":
            logger.debug("Using OAuth authentication")
            key_cert_file = self.jira_config["oauth"]["key_cert_file"]
            with open(key_cert_file, "r") as f:
                key_cert_data = f.read()

            oauth_dict = {
                "access_token": self.jira_config["oauth"]["token"],
                "access_token_secret": self.jira_config["oauth"]["token_secret"],
                "consumer_key": self.jira_config["oauth"]["consumer_key"],
                "key_cert": key_cert_data,
            }
            return JIRA(jira_url, oauth=oauth_dict, options=options)

        # Default: basic auth
        return JIRA(
            jira_url,
            basic_auth=(
                self.jira_config["username"],
                self.jira_config["password"],
            ),
            options=options,
        )
