from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from .forms import LoginForm, ResendVerificationForm, SignUpForm
from .models import User
from .services import send_verification_email, verify_email_token


@require_http_methods(['GET', 'POST'])
def signup(request):
    if request.user.is_authenticated:
        return redirect('store:home')

    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            success, error = send_verification_email(user)
            if success:
                messages.success(
                    request,
                    'Account created! Check your email to verify your address.',
                )
            else:
                messages.warning(
                    request,
                    f'Account created but we could not send the verification email. {error}',
                )
            request.session['pending_verification_email'] = user.email
            return redirect('accounts:verify_email_sent')
    else:
        form = SignUpForm()

    return render(request, 'accounts/signup.html', {'form': form})


@require_http_methods(['GET', 'POST'])
def login_view(request):
    if request.user.is_authenticated:
        return redirect('store:home')

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            messages.success(request, f'Welcome back, {request.user.first_name or "there"}!')
            next_url = request.GET.get('next') or 'store:home'
            return redirect(next_url)
    else:
        form = LoginForm(request)

    return render(request, 'accounts/login.html', {'form': form})


@require_POST
def logout_view(request):
    logout(request)
    messages.info(request, 'You have been signed out.')
    return redirect('store:home')


def verify_email_sent(request):
    email = request.session.get('pending_verification_email', '')
    return render(request, 'accounts/verify_email_sent.html', {'email': email})


@require_http_methods(['GET', 'POST'])
def resend_verification(request):
    if request.method == 'POST':
        form = ResendVerificationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                user = User.objects.get(
                    email__iexact=email,
                    role=User.Role.CUSTOMER,
                )
            except User.DoesNotExist:
                messages.success(
                    request,
                    'If an account exists with that email, a verification link has been sent.',
                )
                return redirect('accounts:login')

            if user.is_email_verified:
                messages.info(request, 'This email is already verified. You can sign in.')
                return redirect('accounts:login')

            success, error = send_verification_email(user)
            if success:
                messages.success(request, 'Verification email sent! Check your inbox.')
                request.session['pending_verification_email'] = user.email
                return redirect('accounts:verify_email_sent')
            messages.error(request, f'Could not send email. {error}')
    else:
        initial = {}
        if email := request.session.get('pending_verification_email'):
            initial['email'] = email
        form = ResendVerificationForm(initial=initial)

    return render(request, 'accounts/resend_verification.html', {'form': form})


def verify_email(request, token):
    user, error = verify_email_token(token)
    if user:
        messages.success(
            request,
            'Email verified successfully! You can now sign in and start ordering.',
        )
        return render(request, 'accounts/email_verified.html', {'user': user})
    messages.error(request, error)
    return render(request, 'accounts/email_verified.html', {'error': error})


@login_required
def profile(request):
    """Simple account overview — will expand in later steps."""
    return render(request, 'accounts/profile.html')
