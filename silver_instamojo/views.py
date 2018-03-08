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

from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpResponse, HttpResponseRedirect

from rest_framework.decorators import api_view

from silver.payment_processors.views import GenericTransactionView

from silver.models.transactions import Transaction

from silver.payment_processors import get_instance
from silver.utils.decorators import get_transaction_from_token

from .utils import verify_instamojo_hmac

class InstamojoTransactionView(GenericTransactionView):
    def get(self, request):
        payment_processor = get_instance(self.transaction.payment_processor)
        payment_processor.execute_transaction(self.transaction, self.request)

        return HttpResponseRedirect(self._get_redirect_url())

    def _get_redirect_url(self):
        return self.transaction.data['longurl']


@api_view(['POST'])
@get_transaction_from_token
def instamojo_webhook_view(request, transaction: Transaction, expired=None):
    payment_processor = get_instance(transaction.payment_processor)

    verify_instamojo_hmac(request.data, payment_processor.salt)

    payment_processor.handle_transaction_response_inner(transaction, request.data['payment_id'])

    # data --
    # amount - Amount related to the payment
    # buyer - Buyer's email
    # buyer_name
    # buyer_phone
    # currency - Currency related to the payment INR
    # fees - Fees charged by Instamojo 125.00
    # longurl - URL related to the payment request
    # mac - Message Authentication code of this webhook request
    # payment_id - ID of the payment
    # payment_request_id - ID of the payment request
    # purpose - Purpose of the Payment request
    # shorturl - Short URL of the payment request
    # status - Status of the Payment. This can be either "Credit" or "Failed".
    
    return HttpResponse(content="OK")
