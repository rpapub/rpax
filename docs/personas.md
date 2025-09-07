Right — thanks for catching that. The **Example Quotes** should be wrapped in proper Markdown blockquote syntax (`>`). Here’s your file corrected:

```markdown
# Personas

This document defines the core personas who can directly benefit from or contribute to the MCP server project.  
It provides context, pain points, goals, and specific value derived from the tool.

## Persona 1: Individual Developer

### Overview
RPA practitioner working mainly in Studio on local projects.  
Needs lightweight tools to better understand, debug, and share workflow content.

### Demographics / Environment
- Role: RPA Developer  
- Environment: corporate laptop, limited permission  
- Technical maturity: medium to high, proficient to follow technical instructions and possibly troubleshoot or ask in a qualified manner for help

### Pain Points
- Project sprawl — hard to keep oversight when juggling multiple or parallel projects  
- Limited AI support — as of 2025, little to no infrastructure is provided for AI-based analysis  
- Vendor gap — no native multi-project tooling provided

### Goals
- Maintain oversight across projects  
- Quickly onboard into new or unfamiliar projects  
- Experiment with workflows and integrations beyond Studio

### Success Metrics
- [blank to fill]  
- [blank to fill]  
- [blank to fill]

### How They Use MCP Server
- Requires access to a host application / MCP client host (dealbreaker)  
- If no host available: uses pseudocode and diagram generator for value  
- Run locally in CLI/stdio mode  
- Parse `.xaml` and `project.json` files to JSON/Markdown  

### Prerequisites

- tbd

### Value Proposition
- Provides multi-project oversight through pseudocode and diagrams  

### Example Quote
> Studio shows me one tree at a time — I need the whole forest.

## Persona 2: CoE / RPA Infrastructure Team

### Overview
Team responsible for operating and governing the enterprise RPA platform.  
They manage environments, permissions, lifecycle policies, and supporting infrastructure,  
with CI/CD pipelines as one part of their mandate. Their challenge is to maintain  
control and demonstrate modernization, including visible adoption of AI practices.

### Demographics / Environment
- Role: CoE Engineer, Platform Administrator, Governance Lead  
- Environment: enterprise RPA platform, environments, permissions, lifecycle policies, CI/CD pipelines  
- Technical maturity: high for RPA platform administration, governance, and reporting; traditional IT administration varies across individuals

### Pain Points
- Organizational pressure to evidence AI adoption, while internal capabilities remain limited  
- Insufficient resourcing for initiatives that demand significant upskilling or specialized expertise

### Goals
- Demonstrate AI adoption in platform operations  
- Maintain low operational overhead with predictable total cost of ownership  
- Reduce dependency on costly vendor-provided tooling

### Success
- Recognized as providing tangible value to development teams  
- Integration outcomes accepted by governance and audit stakeholders  
- Adoption achieved without material increase in platform operating cost

### How They Use MCP Server
- Secure internal hosting for the MCP server within the enterprise platform boundary  
- Collect JSON artifacts into reporting dashboards or audit repositories  
- Configure CI/CD to invoke the parser as a standard step in release workflows  
- Provide governance teams with redacted evidence bundles for compliance reviews

### Prerequisites

- tbd

### Value Proposition
- Supports through multi data lakes lean, repeatable production across multiple client estates  
- Permissive license lowers adoption friction and invites collaboration  

### Example Quote
> “We don’t build tools — we need something ready to plug into the pipeline.”

## Persona 3: Partner Network / Service Providers

### Overview
Organizations that deliver automation as a service — consultancies, managed service providers, and training vendors.  
They often employ individual developers but approach tooling from the perspective of making their production leaner, more repeatable, and more defensible across many clients.

### Demographics / Environment
- Roles: Consultant, Service Delivery Manager, Solution Architect, Trainer  
- Contexts: pre-sales discovery, modernization, managed operations, training programs  
- Constraints: heterogeneous client estates, strict compliance, varied skill levels across staff  
- Technical maturity: high; accustomed to building accelerators and reusing internal frameworks

### Pain Points
- Manual reviews and migrations waste effort and inflate delivery cost  
- Deliverables vary widely across teams, reducing repeatability  
- Clients expect proof of AI adoption, but service providers need to control cost  
- Knowledge transfer and onboarding new staff is inconsistent

### Goals
- Shorten discovery and assessment cycles with standardized insight  
- Build reusable artifacts for audits, governance, and training  
- Lean production: reduce effort per engagement while keeping quality high  
- Enable junior staff to deliver consistent results using standardized outputs  
- Demonstrate AI-readiness to clients without new vendor lock-in

### Success
- Engagements begin with credible, evidence-based insights in days rather than weeks  
- Internal teams adopt a common toolkit across multiple accounts  
- Reduced delivery cost and increased margin through repeatable accelerators  
- Training/onboarding standardized with pseudocode and diagrams

### How They Use MCP Server
- Package parser into internal accelerators for assessment and governance  
- Automate generation of redacted diagnostic bundles for client communication  
- Integrate JSON outputs into proprietary dashboards, checklists, or audit packs  
- Use pseudocode and diagrams in training programs to upskill staff  
- Provide “AI-ready” artifacts to help clients demonstrate adoption within data boundaries

### Adoption Path
- Lab: test on internal portfolio to establish repeatability  
- Package: embed into service methodology (accelerators, templates, dashboards)  
- Field: run in client engagements to reduce manual effort and standardize outputs  
- Scale: integrate as part of managed service operations and training curriculum

### Prerequisites

- tbd

### Example Quotes
> “We can’t afford bespoke work on every client — this gives us lean, repeatable production.”  
> “If we can show clients instant insight into their workflows, we win trust faster.”

# Non-Personas

The following groups are **explicitly out of scope** for the MCP server project.  
They are not the intended users or contributors.

## Non-Persona 1: Citizen Developers / Junior Developers

### Reason
The MCP server requires comfort with CLI tools, repos, and parsing artifacts.  
It is not designed for entry-level users who primarily work only inside Studio.

### Implication
No simplified onboarding, tutorials, or hand-holding are provided.  
Documentation assumes intermediate to advanced technical skills.

## Non-Persona 2: Users Expecting Vendor-Style Support

### Reason
The project is maintained by a solo developer and the community.  
It cannot offer formal support contracts, SLAs, or guarantees of liability.

### Implication
Contributors and adopters are expected to operate independently,  
bear responsibility for their usage, and collaborate on fixes openly.
```

Do you also want a **front-matter block** (YAML at top with title, version, author) so this file fits into your repo’s `docs/` style?
