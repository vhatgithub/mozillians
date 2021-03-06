from django.utils.timezone import now

from django_statsd.clients import statsd
from rest_framework.permissions import BasePermission

from mozillians.api.models import APIv2App


class MozilliansPermission(BasePermission):
    def has_permission(self, request, view):
        api_key = None

        if request.user.is_authenticated():
            api_query = APIv2App.objects.filter(owner=request.user.userprofile)
            if api_query.exists():
                api_key = api_query.order_by('privacy_level')[0].key

        api_key = (request.REQUEST.get('api-key') or request.META.get('HTTP_X_API_KEY') or api_key)

        if api_key:
            try:
                app = APIv2App.objects.get(key=api_key, enabled=True)
            except APIv2App.DoesNotExist:
                statsd.incr('apiv2.auth.failed')
                return False

            request.privacy_level = app.privacy_level

            statsd.incr('apiv2.auth.success')
            statsd.incr('apiv2.requests.app.{0}'.format(app.id))
            statsd.incr('apiv2.requests.total')
            statsd.incr('apiv2.resources.{0}'.format(view.__class__.__name__))

            APIv2App.objects.filter(id=app.id).update(last_used=now())

            return True

        return False
