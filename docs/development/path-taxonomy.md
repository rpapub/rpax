# rpax-lake Path Taxonomy

**Date:** 2026-03-06

This document catalogs every "path"-like concept used across rpax-lake artifacts, defines what each one means, shows its format, and notes which artifacts carry it.

---

## 1. Workflow-level identifiers

### `workflowId`

The primary identifier for a workflow within a project. **Relative POSIX path with `.xaml` extension**, rooted at the project root.

| Artifact | Example value |
|---|---|
| `workflows.index.json` | `Framework/InitAllSettings.xaml` |
| `call-graph.json` (field: `workflow_id`) | `Framework/InitAllSettings.xaml` |
| `workflow-packages/*.json` | `Foo/Bar/myWorkflowFooBar.xaml` |
| `invocations.jsonl` composite `from`/`to` | embedded in composite ID |

> **Note:** `pseudocode/*.json`, `activities.instances/*.json`, and `metrics/*.json` store `workflowId` **without** the `.xaml` extension (e.g. `Framework/InitAllSettings`). This is an open inconsistency — tracked for resolution in a future schema bump.

---

### `id` (Workflow composite ID)

Globally stable composite identifier for a specific version of a workflow file. Stored in `workflows.index.json` as the `id` field of each workflow object.

```
{projectSlug}#{workflowId}#{contentHash16}
```

**Example:**
```
c25v001-core-00000001-8a730ba5#Framework/InitAllSettings.xaml#0dc31bd00f382ae6
```

- `projectSlug` — 8-hex truncated project slug (from `manifest.json`)
- `workflowId` — relative path **with** `.xaml` extension
- `contentHash16` — first 16 hex chars of the file's SHA-256 content hash

Used in `invocations.jsonl` `from`/`to` fields as the full composite string.

---

### `relativePath`

The relative POSIX path of the `.xaml` source file from the project root, **always with `.xaml` extension**. Redundant with `workflowId` in most artifacts but made explicit as a distinct field.

| Artifact | Example value |
|---|---|
| `workflows.index.json` | `Foo/Bar/myWorkflowFooBar.xaml` |
| `pseudocode/*.json` | `Foo/Bar/myWorkflowFooBar.xaml` |
| `expanded-pseudocode/*.expanded.json` | `Foo/Bar/myWorkflowFooBar.xaml` |

---

### `filePath`

Absolute filesystem path to the `.xaml` file on the machine that ran the parse. **Not portable across machines.**

| Artifact | Example value |
|---|---|
| `workflows.index.json` | `/mnt/d/.../Foo/Bar/myWorkflowFooBar.xaml` |
| `manifest.json` (`entryPoints[].filePath`) | `myEntrypointOne.xaml` *(relative, for entry points)* |

---

### `fileName`

Bare filename with extension, no directory component.

| Artifact | Example value |
|---|---|
| `workflows.index.json` | `myWorkflowFooBar.xaml` |

---

### `originalPath`

The raw path string as recorded in UiPath's `project.json` or as discovered on disk, before any normalization. Usually identical to `relativePath`.

| Artifact | Example value |
|---|---|
| `workflows.index.json` | `Foo/Bar/myWorkflowFooBar.xaml` |

---

### `workflowPath`

Used in `workflow-packages/*.json` and `call-graph.json`. Semantically equivalent to `workflowId` (relative path with `.xaml`). Present for legacy/compatibility reasons.

| Artifact | Example value |
|---|---|
| `workflow-packages/*.json` | `Foo/Bar/myWorkflowFooBar.xaml` |
| `call-graph.json` workflows (field: `workflow_path`) | `myEntrypointOne.xaml` |

---

### `projectRoot`

Absolute path to the project root directory on the parse machine. **Not portable.**

| Artifact | Example value |
|---|---|
| `manifest.json` | `/mnt/d/github.com/rpapub/rpax-corpuses/c25v001_CORE_00000001` |
| `workflows.index.json` | same |

---

## 2. Activity-level identifiers

### `activityId`

Globally unique composite identifier for a specific activity within a specific workflow version. Stored in `activities.instances/*.json` as the `activityId` field.

```
{projectId}#{workflowId}#{nodeId}#{contentHash8}
```

**Example:**
```
8551bedf#myEntrypointOne#Activity/LogMessage_2_2#e25a0edb
```

- `projectId` — first 8 chars of the project UUID from `project.json`
- `workflowId` — relative path **without** `.xaml` extension
- `nodeId` — the activity's node ID (see below)
- `contentHash8` — 8 hex chars (first 4 bytes of the node's content hash)

---

### `nodeId` (activities.instances)

A sequential positional path for an activity node, generated during XAML parsing. The format encodes the XML element type and a flat sequential index.

```
{XmlElementType}_{sequentialIndex}
{parentPath}/{XmlElementType}_{depth}_{sequentialIndex}
```

**Examples from `activities.instances/myEntrypointOne.json`:**
```
Activity_1
Activity/LogMessage_2_2
Activity/InvokeWorkflowFile_3_3
Activity/InvokeWorkflowFile_3/InvokeWorkflowFile.Arguments_4
Activity/Sequence_4_5
```

- The root activity uses just `{Type}_{index}`.
- Child activities prepend the parent path: `{parentPath}/{Type}_{depth}_{index}`.
- Dot-notation in the type name (`InvokeWorkflowFile.Arguments`) indicates a property child element.

---

### `nodeId` (activities.tree)

A hierarchical XML traversal path using **index-within-type** notation. The format encodes which Nth occurrence of a given XML element type at each level.

```
Activity/Sequence[0]
Activity/Sequence/LogMessage[0]
Activity/Sequence/InvokeWorkflowFile[0]
```

- `[N]` = 0-based index among sibling elements of the same XML tag name.
- Suitable for XPath-style navigation.
- Distinct from the `nodeId` in `activities.instances` — the two schemas use different positional schemes.

---

### `activityPath` (pseudocode entries)

The XML traversal path for a visual activity node, as stored in the `activities[]` array inside `pseudocode/*.json`.

```
Activity/Sequence
Activity/Sequence/LogMessage
Activity/Sequence/InvokeWorkflowFile
```

- No index suffix — identifies the **element type path**, not a specific instance.
- Used for display and navigation in pseudocode output, not for unique identification.

Also appears in `formattedLine`:
```
- [Main Sequence] Sequence (ActivityPath: Activity/Sequence)
```

---

### `parentActivityId` / `parentId`

Back-reference to the containing activity's identifier.

| Artifact | Field name | Value type |
|---|---|---|
| `activities.instances/*.json` | `parentActivityId` | full `activityId` composite string |
| `activities.tree/*.json` (rootNode tree) | `parentId` | `nodeId` (activities.tree format) |

---

## 3. Project-level identifiers

### `projectId`

The UUID from UiPath's `project.json`. May be a template default UUID if the project was cloned without regenerating the ID. First 8 hex chars are used in `activityId` composites.

| Artifact | Example value |
|---|---|
| `manifest.json` | `8551bedf-7817-4961-9b1f-c844467566a9` |

---

### `projectSlug`

URL-safe, lowercase, hyphenated identifier derived from `projectName-projectId[:8]`. Used in composite IDs and as the lake subdirectory name.

**Example:** `c25v001-core-00000001-8a730ba5`

| Artifact | Example value |
|---|---|
| `workflows.index.json` workflows `id` | embedded prefix |
| `pseudocode/*.json` | `c25v001-core-00000001-8a730ba5` |
| lake subdirectory name | `c25v001-core-0000000-33749f9c71` |

---

## 4. Reference paths

### `targetPath` (invocations.jsonl)

The raw `WorkflowFileName` attribute value from the `InvokeWorkflowFile` XAML element — the path the calling workflow passes to UiPath Studio at design time.

**Example:** `Framework/InitAllSettings.xaml`, `Foo/myEmptyWorkflow.xaml`

This is the *unresolved* reference. The `to` field in the same record holds the resolved composite workflow ID (or `missing:{path}` if resolution failed).

---

### `pathsDir`

Relative path to the `paths/` subdirectory within the lake artifact directory.

| Artifact | Example value |
|---|---|
| `manifest.json` | `paths/` |

---

## 5. Summary table

| Field | Artifact(s) | Extension? | Absolute? | Composite? |
|---|---|---|---|---|
| `workflowId` | `workflows.index.json`, `call-graph.json` | yes (`.xaml`) | no | no |
| `workflowId` | `pseudocode/`, `activities.instances/`, `metrics/` | **no** | no | no |
| `id` (workflow) | `workflows.index.json` | yes (`.xaml`) | no | **yes** (`slug#wfid#hash16`) |
| `relativePath` | `workflows.index.json`, `pseudocode/`, `expanded-pseudocode/` | yes (`.xaml`) | no | no |
| `filePath` | `workflows.index.json`, `manifest.json` entryPoints | yes (`.xaml`) | **yes** | no |
| `fileName` | `workflows.index.json` | yes (`.xaml`) | no | no |
| `originalPath` | `workflows.index.json` | yes (`.xaml`) | no | no |
| `workflowPath` | `workflow-packages/`, `call-graph.json` | yes (`.xaml`) | no | no |
| `projectRoot` | `manifest.json`, `workflows.index.json` | — | **yes** | no |
| `activityId` | `activities.instances/` | no | no | **yes** (`pid#wfid#nid#hash8`) |
| `nodeId` (instances) | `activities.instances/` | no | no | no (positional) |
| `nodeId` (tree) | `activities.tree/` | no | no | no (traversal) |
| `activityPath` | `pseudocode/` entries | no | no | no (type path) |
| `parentActivityId` | `activities.instances/` | no | no | **yes** (activityId format) |
| `parentId` | `activities.tree/` rootNode | no | no | no (nodeId format) |
| `targetPath` | `invocations.jsonl` | yes (`.xaml`) | no | no |

---

## 6. Known inconsistencies

1. **`workflowId` extension inconsistency**: `workflows.index.json` and `call-graph.json` store `workflowId` *with* `.xaml`; `pseudocode/`, `activities.instances/`, and `metrics/` store it *without*. This should be normalized in a future schema bump.

2. **`call-graph.json` snake_case**: Root fields (`project_id`, `project_slug`, `schema_version`, `generated_at`, `entry_points`) and workflow node fields (`workflow_id`, `workflow_path`, `call_depth`) remain snake_case. All other artifact types use camelCase envelope keys. Tracked for future cleanup.

3. **`workflows.index.json` nested `activities[]`**: Each workflow entry contains an `activities[]` list with snake_case fields (`activity_id`, `workflow_id`, `activity_type`, etc.) — these are raw parse-stage objects, not the final `activities.instances` schema. They remain snake_case.

4. **Two `nodeId` formats**: `activities.tree` uses XPath-style `Activity/Sequence[0]`; `activities.instances` uses a sequential positional format `Activity/Sequence_4_5`. Cross-referencing between the two artifacts requires understanding both formats.
