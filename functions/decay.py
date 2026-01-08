import logging
import datetime
from firebase_functions import scheduler_fn
from firestore_client import get_db

# Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configurable values
INACTIVE_PROJECT_DAYS = 30  # Demote projects after 30 days of inactivity

@scheduler_fn.on_schedule(schedule="every day 03:00")
def decay_job(event: scheduler_fn.ScheduledEvent) -> None:
    """
    A scheduled job to perform cleanup and demotion tasks.
    - Deletes expired scratch documents.
    - Demotes inactive project cards to 'archived'.
    """
    logger.info("Starting decay job...")
    db = get_db()
    now = datetime.datetime.now(datetime.timezone.utc)

    # 1. Delete expired scratch docs
    # TODO: Process in batches to avoid memory issues with large result sets.
    scratch_ref = db.collection_group("scratch")
    expired_docs_query = scratch_ref.where("expiresAt", "<=", now)
    expired_docs = list(expired_docs_query.stream())

    deleted_count = 0
    for doc in expired_docs:
        doc.reference.delete()
        deleted_count += 1

    if deleted_count > 0:
        logger.info(f"Deleted {deleted_count} expired scratch documents.")

    # 2. Demote inactive project cards
    projects_ref = db.collection_group("projects")
    inactive_threshold = now - datetime.timedelta(days=INACTIVE_PROJECT_DAYS)

    # NOTE: FIRESTORE INDEX REQUIRED
    # This query requires a composite index on the 'projects' collection group.
    # Create an index with:
    #   - `status` ASC
    #   - `updated_at` ASC
    # The function will fail at runtime without this index.
    # Query for active projects that haven't been touched in a while
    inactive_projects_query = projects_ref.where("status", "==", "active").where("updated_at", "<=", inactive_threshold)
    inactive_projects = list(inactive_projects_query.stream())

    demoted_count = 0
    for doc in inactive_projects:
        doc.reference.update({"status": "archived"})
        demoted_count += 1

    if demoted_count > 0:
        logger.info(f"Demoted {demoted_count} inactive project cards to 'archived'.")

    # 3. Hooks for future work
    handle_reconfirmations()
    handle_contradictions()

    logger.info("Decay job finished.")


def handle_reconfirmations():
    """
    Placeholder for future logic to handle reconfirmation of decayed memories.
    """
    # E.g., find items that were demoted and may need to be resurfaced.
    pass


def handle_contradictions():
    """
    Placeholder for future logic to handle contradictions found during decay.
    """
    # E.g., identify conflicting information that has been archived.
    pass
