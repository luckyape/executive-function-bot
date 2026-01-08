from db import project_repo


def handle_project_command(user_id: str, command_text: str) -> str:
    """
    Handles the /project command and its subcommands.
    """
    parts = command_text.strip().split()
    if not parts:
        return "Invalid /project command. Use /project <subcommand>."

    subcommand = parts[0].lower()
    args = parts[1:]

    if subcommand == "new":
        if not args:
            return "Usage: /project new <name>"
        name = " ".join(args)
        project = project_repo.create_project(user_id, name)
        return f"Project '{project['name']}' created with ID: {project['id']}"

    elif subcommand == "active":
        if not args:
            return "Usage: /project active <projectId>"
        project_id = args[0]
        project_repo.set_active_project(user_id, project_id)
        return f"Project {project_id} is now active."

    elif subcommand == "set":
        if len(args) < 3:
            return "Usage: /project set <projectId> <field> <add|remove|update> <value>"
        project_id, field, operation = args[0], args[1], args[2].lower()
        value = " ".join(args[3:])

        if operation == "add":
            project_repo.add_to_project_list_field(user_id, project_id, field, value)
        elif operation == "remove":
            project_repo.remove_from_project_list_field(user_id, project_id, field, value)
        else:
            project_repo.update_project(user_id, project_id, field, value)

        return f"Project {project_id} updated."

    elif subcommand == "show":
        if not args:
            project = project_repo.get_active_project(user_id)
            if not project:
                return "No active project. Use /project show <projectId>"
        else:
            project_id = args[0]
            project = project_repo.get_project(user_id, project_id)

        if not project:
            return "Project not found."

        # Format the output
        output = f"Project: {project.get('name', 'N/A')} ({project.get('id', 'N/A')})\n"
        output += f"  Goal: {project.get('goal', 'N/A')}\n"
        output += f"  Current State: {project.get('currentState', 'N/A')}\n"
        output += "  Next Steps:\n"
        for step in project.get('nextSteps', []):
            output += f"    - {step}\n"
        output += "  Constraints:\n"
        for constraint in project.get('constraints', []):
            output += f"    - {constraint}\n"
        output += "  Links:\n"
        for link in project.get('links', []):
            output += f"    - {link}\n"
        return output

    elif subcommand == "close":
        if not args:
            return "Usage: /project close <projectId>"
        project_id = args[0]
        project_repo.close_project(user_id, project_id)
        return f"Project {project_id} closed."

    else:
        return f"Unknown subcommand: {subcommand}"
