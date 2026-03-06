"""Code quality review rules for rpax.

Tier 1 rules: checkable from existing artifacts without additional parsing.
"""

from .rules import (
    AnnotationCoverageRule,
    ArgumentNamingRule,
    ErrorHandlingRule,
    OrphanWorkflowRule,
    WorkflowSizeRule,
)

__all__ = [
    "AnnotationCoverageRule",
    "ArgumentNamingRule",
    "ErrorHandlingRule",
    "OrphanWorkflowRule",
    "WorkflowSizeRule",
    "create_review_framework",
]


def create_review_framework(
    config,
    max_workflow_activities: int = 50,
    min_activities_for_checks: int = 10,
):
    """Create a ValidationFramework loaded with Tier 1 review rules.

    Args:
        config: RpaxConfig instance
        max_workflow_activities: Activity count threshold for workflow_size rule
        min_activities_for_checks: Minimum activities before annotation/error-handling checks apply

    Returns:
        ValidationFramework ready to call .validate(artifacts_dir)
    """
    from ..validation.framework import ValidationFramework

    framework = ValidationFramework(config)
    framework.add_rule(ArgumentNamingRule())
    framework.add_rule(WorkflowSizeRule(max_activities=max_workflow_activities))
    framework.add_rule(AnnotationCoverageRule(min_activities=5))
    framework.add_rule(ErrorHandlingRule(min_activities=min_activities_for_checks))
    framework.add_rule(OrphanWorkflowRule())
    return framework
