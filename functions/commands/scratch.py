from ..db.scratch_repo import ScratchRepo
from ..telegram_utils import send_message
from ..firestore_client import db
from firebase_admin import firestore

def handle_scratch_command(message):
    """
    Handles the /scratch command.
    """
    text = message.get('text')
    chat_id = message['chat']['id']
    user_id = message['from']['id']

    parts = text.split(' ', 2)
    subcommand = parts[1] if len(parts) > 1 else 'show'
    args = parts[2] if len(parts) > 2 else ''

    repo = ScratchRepo(str(user_id))

    if subcommand == 'add':
        if not args:
            send_message(chat_id, "Please provide text to add to scratch.")
            return
        scratch_id = repo.add(args)
        send_message(chat_id, f"Added to scratch with ID: {scratch_id}")

    elif subcommand == 'show':
        limit = 10
        if args and args.isdigit():
            limit = int(args)
        entries = repo.get_all(limit=limit)
        if not entries:
            send_message(chat_id, "No scratch entries found.")
            return

        response = "Your scratch entries:\n"
        for entry in entries:
            entry_data = entry.to_dict()
            text = entry_data.get('text', '')
            # Truncate for display
            if len(text) > 75:
                text = text[:72] + "..."
            response += f"- `{entry.id}`: {text}\n"
        send_message(chat_id, response)

    elif subcommand == 'clear':
        repo.clear_all()
        send_message(chat_id, "All scratch entries cleared.")

    elif subcommand == 'promote':
        promote_parts = args.split(' ', 2)
        if len(promote_parts) < 2:
            send_message(chat_id, "Usage: /scratch promote <scratchId> <hot|archive> [tag/project]")
            return

        scratch_id = promote_parts[0]
        target_tier = promote_parts[1]
        tag_or_project = promote_parts[2] if len(promote_parts) > 2 else None

        scratch_entry = repo.get_by_id(scratch_id)

        if not scratch_entry:
            send_message(chat_id, f"Scratch entry with ID {scratch_id} not found.")
            return

        if target_tier not in ['hot', 'archive']:
            send_message(chat_id, "Invalid target tier. Please use 'hot' or 'archive'.")
            return

        # This is a simplified promotion. A real implementation would use a proper repo
        # for the target tier.
        target_collection = db.collection('tasks')

        promoted_task = {
            'user_id': user_id,
            'text': scratch_entry.to_dict()['text'],
            'status': 'pending',
            'tier': target_tier,
            'provenance': {
                'source': 'explicit',
                'scratch_id': scratch_id
            },
            'created_at': firestore.SERVER_TIMESTAMP
        }

        if tag_or_project:
            if target_tier == 'hot':
                promoted_task['tags'] = [tag_or_project]
            else: # archive
                promoted_task['project'] = tag_or_project

        target_collection.add(promoted_task)
        send_message(chat_id, f"Promoted scratch entry {scratch_id} to {target_tier}.")


    else:
        send_message(chat_id, f"Unknown subcommand: {subcommand}. Supported subcommands are: add, show, clear, promote")
