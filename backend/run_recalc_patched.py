import sys
import os
sys.path.append(os.getcwd())
import comprehensive_sync
# Monkey patch GitLab sync
comprehensive_sync.sync_gitlab_commits = lambda *args, **kwargs: 0
comprehensive_sync.sync_gitlab_merge_requests = lambda *args, **kwargs: 0

import recalculate_kpis
