# CodeGen Agent

LLM-assisted code generation that can:
- Generate Python code from a natural-language request
- Execute the AI generated code against *your* variables in a disposable Docker container, and refine codes if error.
- Optionally provide IPython/Jupyter UX.

## Sample

```python
import pandas as pd
import asyncio

from codegen_agent.core.llm_client import create_client, LLMModels
from codegen_agent.core.models import CodeGenerationRequest
from codegen_agent.core.workflow import AgentWorkflow

tips = pd.read_csv("https://raw.githubusercontent.com/mwaskom/seaborn-data/master/tips.csv")

client = create_client(model=LLMModels.GEMINI25_PRO)

request = CodeGenerationRequest(
    request_text="Calculate average tip percentage by day of week and time (lunch/dinner), create a pivot table, and visualize with a heatmap",
    user_variables={"tips_data": tips},
)
workflow = AgentWorkflow(request=request, client=client, max_code_generation=3)

# Generate code and refine until output is satisfactory
result = asyncio.run(workflow.run())
```

## Installation
```bash
pip install codegen-agent@git+https://github.com/yoki/codegen-agent.git@v0.1.0
```

Other than pip, docker container and LLM (Gemini) API setup is needed.

### Docker
Docker must be installed. Tested with docker installed in WSL, not in docker desptop. 

To use in devcontainer, you should install official docker, not repository one, and use fuse-overlayfs (or overlay2). Default vfs is slow (as of Aug 2025). 
```dockerfile
RUN curl -fsSL https://get.docker.com -o get-docker.sh && sh get-docker.sh && rm get-docker.sh
RUN mkdir -p /etc/docker && \
    echo '{\n  "storage-driver": "fuse-overlayfs"\n}' > /etc/docker/daemon.json
```

### API key and other env vars
Create `.env` file:
```bash
GEMINI_API_KEY_FOR_CODEGEN_AGENT=your_gemini_api_key_here
```

**File locations (priority order):**
1. `$CODEGEN_AGENT_DOTENV_PATH` (if set)
2. `./env` (current directory)
3. `/secrets/codegen_agent/.env` (Docker/devcontainer)
4. `~/.config/codegen-agent/.env` (Linux/WSL)
5. `%LOCALAPPDATA%\codegen_agent\codegen_agent\.env` (Windows)

```json
    "mounts": [
        "type=bind,source=/mnt/c/my-path-to-secret,target=/secrets/codegen_agent,readonly",
    ],
```


## Logs

Located at: `<CODEGEN_AGENT_STATE>/log/codegen_agent.log`

Default state directories:
- Linux/WSL: `~/.config/codegen-agent/`
- Windows: `%LOCALAPPDATA%\codegen_agent\State\`

In devcontainer.  
```
    "containerEnv": {
        "CODEGEN_AGENT_STATE": "/workspaces/${localWorkspaceFolderBasename}/codegen_agent_state"
    },

```




## Project Structure

```
codegen_agent/
├── core/
│   ├── execution/          # Docker execution
│   ├── llm_client.py       # LLM interface
│   ├── workflow.py         # Main workflow
│   └── models.py           # Data models
└── ipy/                    # Jupyter integration

samples/                    # Usage examples
sandbox/Dockerfile.runner   # Execution container
```

## Sample output
from `samples/basic.py`

```
**Generated Code (Attempt 1):**
```python
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

# Calculate tip percentage
tips_data['tip_percentage'] = (tips_data['tip'] / tips_data['total_bill']) * 100

# Define the order of days for better visualization
day_order = ['Thur', 'Fri', 'Sat', 'Sun']

# Create a pivot table for average tip percentage by day and time
pivot_table = tips_data.pivot_table(
    values='tip_percentage',
    index=pd.Categorical(tips_data['day'], categories=day_order, ordered=True),
    columns='time',
    aggfunc='mean'
).sort_index()

# Visualize the pivot table with a heatmap
plt.figure(figsize=(8, 6))
sns.heatmap(pivot_table, annot=True, fmt=".2f", cmap="YlGnBu", linewidths=.5)
plt.title('Average Tip Percentage by Day of Week and Time')
plt.xlabel('Time')
plt.ylabel('Day of Week')
plt.show()
```

**Execution Results (Attempt 1):**

STDOUT:
```

```

STDERR:
```
Traceback (most recent call last):
  File "/inputs/prelude.py", line 58, in <module>
    run()
    ~~~^^
  File "/inputs/prelude.py", line 48, in run
    exec(compile(code, CODE_PATH, "exec"), ns, ns)
    ~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/inputs/code.py", line 12, in <module>
    pivot_table = tips_data.pivot_table(
                  ~~~~~~~~~~~~~~~~~~~~~^
        values='tip_percentage',
        ^^^^^^^^^^^^^^^^^^^^^^^^
    ...<2 lines>...
        aggfunc='mean'
        ^^^^^^^^^^^^^^
    ).sort_index()
    ^
  File "/usr/local/lib/python3.13/site-packages/pandas/core/frame.py", line 9516, in pivot_table
    return pivot_table(
        self,
    ...<9 lines>...
        sort=sort,
    )
  File "/usr/local/lib/python3.13/site-packages/pandas/core/reshape/pivot.py", line 102, in pivot_table
    table = __internal_pivot_table(
        data,
    ...<9 lines>...
        sort,
    )
  File "/usr/local/lib/python3.13/site-packages/pandas/core/reshape/pivot.py", line 172, in __internal_pivot_table
    grouped = data.groupby(keys, observed=observed_bool, sort=sort, dropna=dropna)
  File "/usr/local/lib/python3.13/site-packages/pandas/core/frame.py", line 9190, in groupby
    return DataFrameGroupBy(
        obj=self,
    ...<7 lines>...
        dropna=dropna,
    )
  File "/usr/local/lib/python3.13/site-packages/pandas/core/groupby/groupby.py", line 1330, in __init__
    grouper, exclusions, obj = get_grouper(
                               ~~~~~~~~~~~^
        obj,
        ^^^^
    ...<5 lines>...
        dropna=self.dropna,
        ^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "/usr/local/lib/python3.13/site-packages/pandas/core/groupby/grouper.py", line 1043, in get_grouper
    raise KeyError(gpr)
KeyError: 'Sun'

```

**Analysis:** The `KeyError: 'Sun'` occurred because of how the `pd.Categorical` object was created directly within the `pivot_table`'s `index` argument. While syntactically valid, this can sometimes lead to issues with how pandas' internal `groupby` mechanism (used by `pivot_table`) interprets the categories, especially when dealing with the interaction between the temporary Categorical Series and the DataFrame's original column. The error indicates that 'Sun' was a key being processed by the grouper, but it couldn't be found in its internal mapping of valid categories, suggesting a mismatch or misinterpretation of the categorical index.

**Success:** No

**Should Retry:** Yes

**Plan for Next Attempt:** The fix involves explicitly converting the 'day' column of the `tips_data` DataFrame to a `CategoricalDtype` with the desired order *before* calling `pivot_table`. This ensures that the column itself is a properly defined categorical type, which `pivot_table` can then reliably use as an index. This approach is more robust and avoids potential ambiguities when creating a temporary `Categorical` object directly within the `pivot_table` call. The `sort_index()` call is also removed as it becomes redundant once the index is an ordered categorical.


**Execution Results (Attempt 2):**

STDOUT:
```

```

STDERR:
```
/inputs/code.py:16: FutureWarning: The default value of observed=False is deprecated and will change to observed=True in a future version of pandas. Specify observed=False to silence this warning and retain the current behavior
  pivot_table = tips_data.pivot_table(

```

**Analysis:** The previous attempt failed with a `KeyError: 'Sun'`. This error occurred within pandas' internal `groupby` mechanism, which `pivot_table` uses. The traceback points to `get_grouper` failing to find 'Sun' as a key. This is puzzling because 'Sun' is explicitly included in the `day_order` list used to create the `pd.Categorical` type for the 'day' column, and 'Sun' is present in the sample data. The `stderr` also showed a `FutureWarning` regarding the `observed` parameter in `groupby` operations on categorical data. While not an error, this warning suggests a potential area of instability or change in pandas' behavior. It's possible that the default `observed=False` behavior, or an implicit change in it, led to the `KeyError`. Explicitly setting `observed=False` in the `pivot_table` call might resolve this by ensuring all defined categories are considered, regardless of whether they are 'observed' in every specific group combination, aligning with the intended behavior for ordered categorical data.

**Success:** No

**Should Retry:** Yes

**Plan for Next Attempt:** The `KeyError: 'Sun'` is likely related to how pandas' `groupby` (used internally by `pivot_table`) handles categorical columns, especially in light of the `FutureWarning` about the `observed` parameter. To address this, I will explicitly set `observed=False` in the `pivot_table` call. This should ensure that all categories defined in the `day_order` are considered during the grouping, potentially resolving the `KeyError` and silencing the warning. The rest of the code, including the tip percentage calculation, categorical conversion, and heatmap visualization, appears correct and will be retained.


**Execution Results (Attempt 3):**
```

```

**Code Assessment:** The generated code meets the requirements.

*Code has been saved:*

```python
# User request: Calculate average tip percentage by day of week and time (lunch/dinner), create a pivot table, and visualize with a heatmap

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

# Calculate tip percentage
tips_data['tip_percentage'] = (tips_data['tip'] / tips_data['total_bill']) * 100

# Define the order of days for better visualization
day_order = ['Thur', 'Fri', 'Sat', 'Sun']

# Convert 'day' column to a Categorical type with the specified order
# This is a more robust way to ensure the categories are correctly set
tips_data['day'] = pd.Categorical(tips_data['day'], categories=day_order, ordered=True)

# Create a pivot table for average tip percentage by day and time
pivot_table = tips_data.pivot_table(
    values='tip_percentage',
    index='day',
    columns='time',
    aggfunc='mean',
    observed=False # Explicitly set observed to False to handle categorical groups consistently
)

# Visualize the pivot table with a heatmap
plt.figure(figsize=(8, 6))
sns.heatmap(pivot_table, annot=True, fmt=".2f", cmap="YlGnBu", linewidths=.5)
plt.title('Average Tip Percentage by Day of Week and Time')
plt.xlabel('Time')
plt.ylabel('Day of Week')
plt.show()

```