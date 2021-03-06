# Copyright (c) 2018 Draftspotting Technologies Pvt Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from django.conf.urls import include, url

from silver.views import pay_transaction_view, complete_payment_view

from .views import instamojo_webhook_view

urlpatterns = [
    url(r'instamojo/(?P<token>[0-9a-zA-Z-_\.]+)/webhook$',
        instamojo_webhook_view, name='instamojo-webhook'),
    url(r'pay/(?P<token>[0-9a-zA-Z-_\.]+)/$',
        pay_transaction_view, name='payment'),
    url(r'pay/(?P<token>[0-9a-zA-Z-_\.]+)/complete$',
        complete_payment_view, name='payment-complete')
]
