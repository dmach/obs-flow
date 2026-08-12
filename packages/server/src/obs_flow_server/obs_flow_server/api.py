from django_bolt import BoltAPI

api = BoltAPI()


# Import API endpoints to register them with BoltAPI
import pull_requests.api
import staging.api

# Mount Django ASGI app at the root path to serve standard Django views
api.mount_django("/", clear_root_path=True)
