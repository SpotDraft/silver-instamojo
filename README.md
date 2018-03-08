# silver-instamojo [![Build Status](https://travis-ci.org/spotdraft/silver-instamojo.svg?branch=master)](https://travis-ci.org/spotdraft/silver-instamojo)

Instamojo Payment Processor implementation for silver

```py
# put this in your settings.py
instamojo_setup_data = {
    'endpoint': 'https://test.instamojo.com/api/1.1/', # or https://www.instamojo.com/api/1.1/
    'api_key': INSTAMOJO_API_KEY,
    'auth_token': INSTAMOJO_AUTH_TOKEN,
    'salt': INSTAMOJO_SALT
}

PAYMENT_PROCESSORS = {
    'instamojo_triggered': {
        'class': 'silver_instamojo.payment_processors.InstamojoTriggered',
        'setup_data': instamojo_setup_data,
    },
}
```
