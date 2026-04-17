## M3 – Issue 4: Implement Restore Command (Stub)

**Status:** Completed – Architectural Stub Implemented  
**Purpose:** Provide the structural entry point for data restoration. Full logic will be implemented in Milestones M4–M5.

### Description
The restore command prepares the framework for restoring user data on the Linux target system. Although full implementation is beyond the current milestone's scope, the stub:

- Loads project configuration
- Accepts a backup source directory
- Integrates with the CLI architecture
- Documents the full restoration workflow
- Makes the framework operational for demonstration purposes

### Stub Functionality
The command currently prints the intended behavior:

1. Load manifest.json  
2. Validate backup source  
3. Recreate directory structure  
4. Copy files to Linux home directory  
5. Validate file integrity with hashes  
6. Produce restore report  

### Demonstration
The command can be executed as:

```
python -m src.cli restore --source /mnt/backup
```


### Output Files (Future)
- Restored user home directories  
- Restore summary report  
- Hash validation results  

### Academic Value
This issue establishes the architectural layer required for post-migration restoration and prepares the project for Milestone M4 without prematurely implementing complex logic.

