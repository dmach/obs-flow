from django.core.exceptions import ObjectDoesNotExist
from django_bolt import BoltAPI
from django_bolt.exceptions import NotFound, BadRequest


class ExceptionHandlerMiddleware:
    """
    Translate Django exceptions into Bolt Exceptions.
    """
    def __init__(self, app):
        self.app = app

    async def __call__(self, request):
        try:
            return await self.app(request)
        except ObjectDoesNotExist as exc:
            msg = " ".join((str(i) for i in exc.args))
            raise NotFound(detail=msg)
        except ValueError as exc:
            msg = " ".join((str(i) for i in exc.args))
            raise BadRequest(detail=msg)


api = BoltAPI(middleware=[ExceptionHandlerMiddleware])


# Import API endpoints to register them with BoltAPI
import pull_requests.api
import staging.api
import reviews.api

# Mount Django ASGI app at the root path to serve standard Django views
api.mount_django("/", clear_root_path=True)
