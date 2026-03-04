# pull-epic

Pull the next epic and its associated issues from origin — or a specific epic or issue if named in the invocation. Have a researcher agent do the fetching; the JSON returns eat context for no reason if read directly.

Once you have the issue contents, create an appropriately named feature branch off the integration branch (dev, develop, or main if no integration branch exists). Run a quick explorer pass on the current codebase state — issues are written at planning time and the codebase may have moved since.

Brief on what we're working on and where things stand, then chain to /design to think through the approach, or /build if the plan is already clear.
