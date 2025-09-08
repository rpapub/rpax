# ADR-000: ADR Maintenance Lifecycle and Update Process

**Status:** Approved  
**Date:** 2025-09-08  
**Deciders:** Development Team  

## Context

Architecture Decision Records (ADRs) capture important technical decisions but become outdated as implementations evolve. We need a systematic process for maintaining ADR accuracy and relevance, especially when working with AI assistants like Claude that may need to update documentation to reflect implementation reality.

The rpax project has experienced significant implementation evolution (v0.0.1 → v0.0.3) where ADRs lagged behind actual code, causing confusion about current architecture and decisions.

## Decision

Establish a formal ADR maintenance lifecycle with specific processes for updates, reviews, and AI assistant guidance.

### ADR Status Lifecycle

ADRs progress through these states:

```
Proposed → Under Review → Approved → Implemented → [Amended | Superseded | Deprecated]
```

**Status Definitions:**
- **Proposed**: Initial draft, awaiting review
- **Under Review**: Being evaluated by stakeholders  
- **Approved**: Accepted for implementation
- **Implemented**: Decision has been coded and deployed
- **Amended**: Updated to reflect implementation changes (original decision intact)
- **Superseded**: Replaced by newer ADR (reference new ADR number)
- **Deprecated**: No longer applicable, kept for historical context

### Update Process

**1. Identification Phase**
- ADRs requiring updates are identified through:
  - user input
  - Code review processes
  - Architecture documentation audits
  - Implementation milestone reviews
  - AI assistant analysis during development

**2. Change Classification**
- **Editorial**: Typos, formatting, clarification (no approval needed)
- **Amendment**: Implementation details changed, core decision unchanged (requires approval)  
- **Superseding**: Core decision changed, new ADR needed (requires full review)

**3. Update Execution**
- All non-editorial changes require explicit user approval
- Updates include date stamps and change documentation
- Original decision context preserved in amendments

### Instructions for AI Assistants (LLMs)

When working with ADRs, follow this process:

#### **Before Making Any Changes**
1. **Read the current ADR completely** to understand context and current status
2. **Identify change type**: Editorial, Amendment, or Superseding
3. **Never make non-editorial changes without explicit user approval**

#### **For Editorial Changes**
- Fix typos, formatting, broken links
- Clarify wording without changing meaning
- Update dates if user confirms current date

#### **For Amendment Changes**
```markdown
**REQUIRED STEPS:**
1. Ask user: "I need to amend ADR-XXX to reflect [specific changes]. This requires approval. Proceed?"
2. Wait for explicit approval before proceeding
3. Update status to "Amended (Updated YYYY-MM-DD)"  
4. Add "Amendment Notes (YYYY-MM-DD)" section explaining changes
5. Preserve original decision context
6. Update implementation status if needed
```

#### **For Superseding Changes**
```markdown
**REQUIRED STEPS:**
1. Ask user: "ADR-XXX needs major changes that supersede the original decision. Should I create ADR-XXX (new) or amend existing?"
2. If creating new ADR:
   - Create new ADR with incremented number
   - Update old ADR status to "Superseded by ADR-XXX"
   - Reference old ADR in new ADR context section
```

#### **Standard Amendment Template**
When amending ADRs, use this format:

```markdown
# ADR-XXX: [Original Title]

**Status:** Amended (Updated YYYY-MM-DD)
**Original Date:** YYYY-MM-DD  
**Updated:** YYYY-MM-DD

## Amendment Notes (YYYY-MM-DD)

**What Changed**: [Brief summary of changes]
**Why Amended**: [Reason for update - implementation evolution, new requirements, etc.]
**Impact**: [What this means for current/future work]

## Context
[Original context preserved]

## Decision  
[Updated decision with changes clearly marked or explained]

## Implementation Status (Updated YYYY-MM-DD)
[Current status of decision implementation]
```

#### **Validation Checklist**
Before submitting ADR changes, verify:
- [ ] User approval obtained for non-editorial changes
- [ ] Status correctly updated with date
- [ ] Amendment notes explain what and why
- [ ] Original context preserved
- [ ] Related ADRs referenced if affected
- [ ] Implementation status reflects reality

### Code Review Integration

**ADR Updates Trigger Code Review When:**
- Status changes from Proposed → Approved
- Implementation status updated to "Implemented"
- Major amendments affecting multiple ADRs
- New ADRs superseding existing ones

**Review Criteria:**
- Technical accuracy against current codebase
- Consistency with related ADRs  
- Clear documentation of changes and rationale
- Appropriate status transition

## Examples

### Example 1: Implementation Evolution Amendment
```markdown
**Status:** Amended (Updated 2025-09-08)

## Amendment Notes (2025-09-08)
**What Changed**: Layer 2 redefined from "Validation/CI" to "Transformation/Enhancement"
**Why Amended**: Implementation evolved beyond original scope, added V0 schema and activity resources
**Impact**: Architecture documentation now matches actual implementation
```

### Example 2: Superseding Decision
```markdown
# ADR-025: Original Authentication Approach
**Status:** Superseded by ADR-030 (2025-09-08)

# ADR-030: New Authentication Architecture  
**Status:** Proposed
**Supersedes:** ADR-025
```

## Consequences

**Positive:**
- Maintains ADR accuracy and relevance
- Clear process for AI assistants prevents unauthorized changes
- Preserves decision history and evolution
- Integrates with existing code review processes

**Negative:**
- Additional overhead for documentation maintenance
- Requires discipline to keep ADRs current
- May slow down rapid iteration if over-applied

**Neutral:**
- Establishes clear accountability for architectural documentation
- Creates audit trail for decision evolution

## Related ADRs

- ADR-002: Layered Architecture (example of amended ADR)
- ADR-003: CLI Surface (example of implementation status updates)
- Future ADRs will follow this maintenance process

## Implementation

This ADR takes effect immediately. All future ADR updates must follow this process.

**Next Steps:**
1. Review existing ADRs for status accuracy
2. Update development workflow to include ADR review checkpoints
3. Train AI assistants on this process
4. Establish regular ADR maintenance schedule (quarterly reviews)