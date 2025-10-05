"""Celery tasks for executing Obsidian Vault workflows."""

import shutil
import time
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from src.clients.github_client import GithubClient
from src.config.settings import get_settings
from src.db.database import get_db
from src.db.models.workflow import Workflow, WorkflowStatus
from src.services.vault import VaultService
from src.tasks.celery_app import celery_app
from src.workflows.orchestrator import WorkflowOrchestrator

settings = get_settings()


@celery_app.task(bind=True, name="run_workflow_task")
def run_workflow_task(self, workflow_id: int) -> None:
    """
    Execute a complete workflow: clone repo, run agents, commit, create PR.

    This task orchestrates the entire workflow lifecycle:
    1. Retrieve workflow from database
    2. Clone repository to temporary directory
    3. Analyze vault and execute agents via WorkflowOrchestrator
    4. Apply changes to local clone via VaultService
    5. Commit and push changes via GithubClient
    6. Create pull request on GitHub
    7. Update workflow status and store results
    8. Clean up temporary directory

    Args:
        workflow_id: Database ID of the workflow to execute

    Raises:
        Exception: Any error during workflow execution (caught and stored in DB)
    """
    # Get database session
    db: Session = next(get_db())
    workflow = None
    temp_path = None

    try:
        # 1. Retrieve workflow from database
        workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found")

        # 2. Update status to RUNNING
        workflow.status = WorkflowStatus.RUNNING
        workflow.started_at = datetime.now(timezone.utc)
        workflow.celery_task_id = self.request.id
        db.commit()

        # 3. Initialize services
        github_service = GithubClient()
        vault_service = VaultService()
        orchestrator = WorkflowOrchestrator()

        # 4. Create temporary directory for vault clone
        clone_base_path = Path(settings.WORKFLOW_CLONE_BASE_PATH)
        clone_base_path.mkdir(parents=True, exist_ok=True)
        temp_path = clone_base_path / f"workflow_{workflow_id}_{self.request.id}"

        # 5. Clone repository
        github_service.clone_repository(
            target_path=temp_path,
            branch=settings.WORKFLOW_DEFAULT_BRANCH,
        )

        # 6. Analyze vault and create workflow plan
        workflow_plan = orchestrator.analyze_vault(temp_path)

        # Store strategy in workflow
        workflow.strategy = workflow_plan.strategy
        db.commit()

        # 7. Execute workflow
        workflow_result = orchestrator.execute_workflow(temp_path, workflow_plan)

        if not workflow_result.success:
            raise Exception(f"Workflow execution failed: {workflow_result.summary}")

        # 8. Apply changes to vault
        vault_service.apply_changes(temp_path, workflow_result.changes)

        # 9. Validate vault structure after changes
        if not vault_service.validate_vault_structure(temp_path):
            raise Exception("Vault structure validation failed after applying changes")

        # 10. Create new branch for changes
        branch_name = f"obsidian-agents/{workflow_id}-{workflow_plan.strategy}"
        github_service.create_branch(repo_path=temp_path, branch_name=branch_name)

        # 11. Commit and push changes
        commit_message = f"""Automated vault improvements via {workflow_plan.strategy} strategy

{workflow_result.summary}

Changes made by Obsidian Agents workflow #{workflow_id}
"""
        pushed = github_service.commit_and_push(
            repo_path=temp_path, branch_name=branch_name, message=commit_message
        )

        # If no changes were made, complete workflow successfully without creating PR
        if not pushed:
            workflow.status = WorkflowStatus.COMPLETED
            workflow.completed_at = datetime.now(timezone.utc)
            workflow.workflow_metadata = {
                "agent_results": workflow_result.agent_results,
                "total_changes": 0,
                "branch_name": branch_name,
                "message": "Workflow completed successfully with no changes to commit",
            }
            db.commit()
            return

        # 12. Create pull request
        pr_title = f"Automated vault improvements ({workflow_plan.strategy})"
        pr_body = f"""## Automated Vault Improvements

**Workflow ID**: #{workflow_id}
**Strategy**: {workflow_plan.strategy}

### Summary
{workflow_result.summary}

### Details
- **Total Changes**: {len(workflow_result.changes)} file operations
- **Agents Executed**: {len(workflow_result.agent_results)}

### Agent Results
"""
        for agent_name, result in workflow_result.agent_results.items():
            pr_body += f"\n#### {agent_name}\n"
            pr_body += (
                f"- Status: {'✅ Success' if result['success'] else '❌ Failed'}\n"
            )
            pr_body += f"- Message: {result['message']}\n"
            pr_body += f"- Changes: {result['changes_count']}\n"

        pr_body += "\n---\n*Generated by Obsidian Agents Workflow Automation*"

        pr = github_service.create_pull_request(
            repo_full_name=settings.GITHUB_REPO_FULL_NAME,
            head_branch=branch_name,
            title=pr_title,
            body=pr_body,
        )

        # 13. Update workflow to COMPLETED
        workflow.status = WorkflowStatus.COMPLETED
        workflow.completed_at = datetime.now(timezone.utc)
        workflow.pr_url = pr.html_url
        workflow.workflow_metadata = {
            "agent_results": workflow_result.agent_results,
            "total_changes": len(workflow_result.changes),
            "branch_name": branch_name,
        }
        db.commit()

    except Exception as e:
        # Update workflow to FAILED
        if workflow:
            workflow.status = WorkflowStatus.FAILED
            workflow.completed_at = datetime.now(timezone.utc)
            workflow.error_message = str(e)
            db.commit()

        # Re-raise exception for Celery to handle
        raise

    finally:
        # 14. Clean up temporary directory
        if temp_path and temp_path.exists():
            try:
                shutil.rmtree(temp_path)
            except Exception as cleanup_error:
                # Log cleanup error but don't fail the task
                print(f"Warning: Failed to clean up {temp_path}: {cleanup_error}")

        # Close database session
        db.close()


@celery_app.task(name="cleanup_old_workflows")
def cleanup_old_workflows() -> None:
    """
    Periodic task to clean up old workflow temporary directories.

    This task should be scheduled to run periodically (e.g., daily) to
    ensure that any orphaned temporary directories are cleaned up.
    """
    clone_base_path = Path(settings.WORKFLOW_CLONE_BASE_PATH)

    if not clone_base_path.exists():
        return

    # Clean up any workflow_* directories older than 1 day
    current_time = time.time()
    for temp_dir in clone_base_path.glob("workflow_*"):
        if temp_dir.is_dir():
            # Check if directory is older than 24 hours
            dir_age = current_time - temp_dir.stat().st_mtime
            if dir_age > 86400:  # 24 hours in seconds
                try:
                    shutil.rmtree(temp_dir)
                    print(f"Cleaned up old workflow directory: {temp_dir}")
                except Exception as e:
                    print(f"Failed to clean up {temp_dir}: {e}")
