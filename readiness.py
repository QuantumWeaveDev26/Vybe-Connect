"""Private operator preflight. No network calls, database writes or secret output."""
import json
import os


def snapshot():
    from business_providers import status, plans
    from embedded_signup import configuration as meta_configuration
    from google_connections import configuration as google_configuration
    from recovery_mail import configuration as mail_configuration

    def configured(check):
        try:return bool(check())
        except (ValueError,TypeError,OSError):return False

    checks={
        'subscription_checkout':configured(lambda: status(None,'billing')['ready'] and plans()),
        'platform_ai':bool(os.environ.get('TW_PLATFORM_AI_MANAGED','false').lower()=='true'
                           and os.environ.get('TW_AI_ENABLED','false').lower()=='true'
                           and os.environ.get('TW_OPENAI_API_KEY')
                           and os.environ.get('TW_AI_MODEL')=='gpt-6-luna'),
        'meta_onboarding':configured(lambda:meta_configuration()['ready']),
        'recovery_email':configured(lambda:mail_configuration()['ready']),
        'google_connections':configured(lambda:google_configuration()['ready'])}
    return {'configuration':{name:'configured' if ready else 'setup_needed' for name,ready in checks.items()},
            'live_acceptance':'not_established',
            'pending_acceptance':['OpenAI inference and agent quality','Razorpay subscription lifecycle',
                                  'Meta approval, onboarding and delivery','Recovery mailbox delivery',
                                  'Payment and shipping operations','Physical devices and backup restore'],
            'ready_for_paying_customers':False}


if __name__=='__main__':
    print(json.dumps(snapshot(),indent=2))
    # Configuration alone cannot certify live customer readiness.
    raise SystemExit(2)
