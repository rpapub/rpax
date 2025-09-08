# rpax - See Your UiPath Projects Like Never Before! 🔍

**For RPA Developers**: Instantly understand your UiPath workflows, find problems, and create documentation - all with simple commands!

✅ **Find workflows that call non-existent workflows** (before your bot crashes!)  
✅ **See which workflows are never used** (orphans you can safely delete)  
✅ **Generate visual diagrams** of your workflow relationships  
✅ **Validate your project** before deployment  
✅ **Get detailed reports** about any workflow  

---

## Problems rpax Solves For You

🔴 **"I don't know what calls what in my project"**  
→ rpax shows you exactly which workflows call which other workflows

🔴 **"My workflow fails with 'file not found' in production"**  
→ rpax finds missing workflow references **before** you deploy

🔴 **"I need to document my project structure for my manager"**  
→ rpax generates visual diagrams automatically (no more PowerPoint!)

🔴 **"Which workflows can I safely delete?"**  
→ rpax finds orphan workflows that are never called by anything

🔴 **"I have circular dependencies and don't know where"**  
→ rpax detects when Workflow A calls Workflow B calls Workflow A

---

## Installation - Just Copy & Paste! 

### Step 1: Install Python (One Time Only)

1. **Download Python**: [Click here to download Python 3.11](https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe)
2. **Run the installer**
3. ⚠️ **CRITICAL**: Check the box ✅ **"Add Python to PATH"** at the bottom
4. Click **"Install Now"**
5. Wait for installation to finish

### Step 2: Open PowerShell

1. Press **Windows key**
2. Type: **powershell**
3. Press **Enter**

### Step 3: Install rpax (Copy & Paste These Commands)

Copy each line one at a time and press Enter after each:

```powershell
# Install the uv tool
pip install uv
```

```powershell
# Download rpax from GitHub
git clone https://github.com/rpapub/rpax.git
```

```powershell
# Enter the rpax folder
cd rpax
```

```powershell
# Install rpax with all dependencies
uv sync
```

✅ **Done!** rpax is now installed and ready to use.

---

## How To Use rpax - Real Examples

### 🔍 **Check Your Project for Problems**

You can specify either the project folder OR the project.json file directly:

```powershell
# Option 1: Point to project folder (traditional way)
uv run rpax parse "C:\Your\Project\Path"

# Option 2: Point directly to project.json file (NEW!)
uv run rpax parse "C:\Your\Project\Path\project.json"

# Step 2: Check for problems
uv run rpax validate .rpax-lake
```

**What you'll see:**
```
✅ All workflows found (21/21)
❌ 2 missing workflows detected:
   - ProcessData.xaml calls GetUserData.xaml (NOT FOUND)
   - MainFlow.xaml calls ArchiveFiles.xaml (NOT FOUND)
⚠️ 3 orphan workflows found (never called by anything):
   - TestWorkflow.xaml
   - OldBackupProcess.xaml  
   - Deprecated_LoginFlow.xaml
```

### 📊 **Generate Visual Diagram**

```powershell
uv run rpax graph calls --path .rpax-lake --out my-project-diagram.mmd
```

This creates a `my-project-diagram.mmd` file. Open it in Notepad to see a text diagram, or paste the contents into [Mermaid Live Editor](https://mermaid.live/) to see a beautiful visual diagram.

### 📋 **List All Your Workflows**

```powershell
# Basic list
uv run rpax list workflows --path .rpax-lake

# Search for specific workflows
uv run rpax list workflows --path .rpax-lake --search "Login"

# Show as table with details
uv run rpax list workflows --path .rpax-lake --format table --verbose
```

### 🗂️ **Discover Projects in Your Lake**

```powershell
# List all projects in your lake
uv run rpax list-projects --path .rpax-lake

# Search for specific projects
uv run rpax list-projects --path .rpax-lake --search "calc"

# Get JSON output for tooling
uv run rpax list-projects --path .rpax-lake --format json
```

### 🔎 **Find Unused Workflows (Orphans)**

```powershell
uv run rpax list orphans --path .rpax-lake
```

### 🔍 **Get Details About Any Workflow**

```powershell
uv run rpax explain "MainWorkflow.xaml" --path .rpax-lake
```

**What you'll see:**
```
📄 MainWorkflow.xaml
├── 📁 Arguments: username, password, environment
├── 📁 Variables: loginResult, userID
├── 🔗 Calls: LoginFlow.xaml, ProcessData.xaml
├── 📞 Called by: project.json (main entry point)
└── 📊 Size: 15.2 KB, Modified: 2024-09-05
```

---

## Common Workflows

### **Before Deploying to Production**
```powershell
# Parse and validate your project (from anywhere!)
uv run rpax parse "C:\Your\Project\Path\project.json"
uv run rpax validate .rpax-lake

# If no errors, you're good to deploy! 🚀
```

### **Documenting Your Project**
```powershell
# Create visual diagram
uv run rpax graph calls --path .rpax-lake --out project-structure.mmd

# Create workflow list for documentation
uv run rpax list workflows --path .rpax-lake --format csv --out workflow-list.csv
```

### **Cleaning Up Old Code**
```powershell
# Find workflows that are never called
uv run rpax list orphans --path .rpax-lake

# Find workflows with circular dependencies
uv run rpax validate .rpax-lake --rule cycles
```

---

## If Something Doesn't Work

### **"pip is not recognized"**
→ You forgot to check "Add Python to PATH" during installation  
→ Reinstall Python and make sure to check that box ✅

### **"git is not recognized"**  
→ Install Git from: https://git-scm.com/downloads/win  
→ Use all default settings, just keep clicking "Next"

### **"Cannot find project.json"**
→ Make sure your path points to the UiPath project folder  
→ The folder should contain a `project.json` file  
→ Example: `"C:\UiPath\Projects\MyBot"` not `"C:\UiPath\Projects\MyBot\Main.xaml"`

### **"Permission denied" or "Access denied"**
→ Run PowerShell as Administrator  
→ Right-click PowerShell → "Run as Administrator"

### **Still having problems?**
→ Report issues here: [GitHub Issues](https://github.com/rpapub/rpax/issues)  
→ Include the exact error message you're seeing

---

## What rpax Creates

When you run rpax, it creates these files in the output folder:

- **📄 manifest.json** — Your project info (name, version, dependencies)
- **📄 workflows.index.json** — Complete list of all workflows found
- **📄 invocations.jsonl** — Which workflow calls which workflow
- **📄 calls-graph.mmd** — Visual diagram of your project structure

You can open all `.json` files in Notepad to see the data, or use online JSON viewers for prettier formatting.

---

## Current Version

**rpax v0.0.3** - Advanced implementation with resource model and error collection  
**Status**: 🚀 Released - Enhanced parsing with V0 schema, activity resources, and diagnostics  
**Installation**: Development setup required (see Installation section above)  
**Next**: v0.3.0 consumption validation, PyPI distribution, HTTP API layer

---

## License & Support

- **License**: [Creative Commons Attribution (CC-BY)](https://creativecommons.org/licenses/by/4.0/) - Free to use!  
- **Issues**: [Report problems here](https://github.com/rpapub/rpax/issues)  
- **Authors**: See [AUTHORS.md](AUTHORS.md) for contributors

---

*Made with ❤️ for the RPA community*