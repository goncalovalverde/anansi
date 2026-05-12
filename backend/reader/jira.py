from jira import JIRA
import dateutil.parser
import logging
from pandas import NaT, DataFrame

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
            # Try direct attribute access first
            sp_value = getattr(issue.fields, story_points_field, None)
            
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
        """Fetch issues using python-jira library, requesting custom fields explicitly."""
        jira = self.get_jira_instance()
        issues = []
        i = 0
        chunk_size = 100
        
        # Build list of custom fields to request
        fields_to_request = [
            "key", "issuetype", "creator", "summary", "created", "status",
            "changelog", "parent"
        ]
        
        # Add custom field IDs if configured
        if self.jira_config.get("story_points_field"):
            fields_to_request.append(self.jira_config["story_points_field"])
        if self.jira_config.get("epic_link_field"):
            fields_to_request.append(self.jira_config["epic_link_field"])
        
        # Request all custom fields as fallback
        fields_str = ",".join(fields_to_request) + ",customfield_*"
        logger.info(f"Requesting fields: {fields_str}")
        
        while True:
            chunk = jira.search_issues(
                self.jira_config["jql_query"],
                expand="changelog",
                fields=fields_str,
                maxResults=chunk_size,
                startAt=i,
            )
            i += chunk_size
            for issue in chunk.iterable:
                # Debug first issue to check available attributes
                if len(issues) == 0:
                    story_points_field = self.jira_config.get("story_points_field")
                    sp_value = getattr(issue.fields, story_points_field, None)
                    logger.info(f"First issue {issue.key}: {story_points_field} = {sp_value} (type: {type(sp_value).__name__})")
                issues.append(issue)
            
            if progress_callback:
                progress_callback(len(issues), chunk.total)
            if i >= chunk.total:
                break
        logger.info(f"Fetched {len(issues)} issues from Jira")
        return issues

    def get_jira_data(self, progress_callback=None) -> DataFrame:
        logger.info("=== FETCHING Jira data from API ===")
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
