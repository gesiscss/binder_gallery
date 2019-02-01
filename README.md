Binder Gallery

Example how to fill BinderLaunch table
```python
from datetime import datetime
import requests
token = ''
# token = token.decode()
headers = {'Authorization': 'Bearer ' + token}
timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
data = {'schema': 'test schema', 'version': '1.0', 'timestamp': timestamp, 
        'provider': 'gh', 'spec': 'gesiscss/orc/ref', 'status': 'success'}
requests.post('http://127.0.0.1:5000/admin/binderlaunch/new/', data=data, headers=headers)
```