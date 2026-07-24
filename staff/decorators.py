from django.contrib import messages
from django.shortcuts import redirect


def staff_required(view_func):
    """
    Decorator that restricts access to users with STAFF or ADMIN roles.
    Redirects non-staff users to the home page with an error message.
    """
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Please sign in to access the staff panel.')
            return redirect('accounts:login')

        if not (request.user.is_staff_user or request.user.is_admin_user):
            messages.error(request, 'You do not have permission to access the staff panel.')
            return redirect('store:home')

        return view_func(request, *args, **kwargs)

    return _wrapped_view

