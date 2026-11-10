"""Give existing users the deterministic dev token `flow-<username>`.

Run through `manage.py shell < scripts/ensure_user_tokens.py` with USERS (space separated)
in the environment. Users must already exist.
"""

import hashlib
import os

from accounts.models import Token, User

for username in os.environ["USERS"].split():
    user = User.objects.get(username=username)
    raw = f"flow-{username}"
    token_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    if not Token.objects.filter(user=user, token_hash=token_hash).exists():
        Token.objects.create(user=user, token_hash=token_hash, last_eight=raw[-8:], description="populate_test_data.sh")
