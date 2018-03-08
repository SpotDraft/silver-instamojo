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

import json
import logging
from furl import furl

from django_fsm import TransitionNotAllowed

from django.contrib.sites.shortcuts import get_current_site
from django.dispatch import receiver
from django.utils.dateparse import parse_datetime
from django.urls import reverse

from instamojo_wrapper import Instamojo

from silver.models import Transaction
from silver.payment_processors import PaymentProcessorBase
from silver.payment_processors.forms import GenericTransactionForm
from silver.payment_processors.mixins import (TriggeredProcessorMixin,
                                              ManualProcessorMixin)
from silver.utils.payments import _get_jwt_token, get_payment_complete_url

from silver_instamojo.views import InstamojoTransactionView
from silver_instamojo.models import InstamojoPaymentMethod

logger = logging.getLogger(__name__)


class InstamojoBase(PaymentProcessorBase):
    payment_method_class = InstamojoPaymentMethod
    transaction_view_class = InstamojoTransactionView
    allowed_currencies = ('INR', )

    instamojo_wrapper = None
    salt = None

    def __init__(self, name, *args, **kwargs):
        super(InstamojoBase, self).__init__(name)

        self.salt = kwargs['salt']
        self.instamojo_wrapper = Instamojo(
            kwargs['api_key'], auth_token=kwargs['auth_token'], endpoint=kwargs['endpoint'] or "https://www.instamojo.com/api/1.1/")

    def refund_transaction(self, transaction, payment_method=None):
        # NOT IMPLEMENTED
        pass

    def void_transaction(self, transaction, payment_method=None):
        # NOT IMPLEMENTED
        pass

    def handle_transaction_response_inner(self, transaction: Transaction, payment_id):
        response = self.instamojo_wrapper.payment_detail(payment_id)

        print(response)
        if 'success' in response and not response['success']:
            logger.info("Failed to load payment info %r", response['message'])
            transaction.fail(fail_reason=response['message'])
            return

        payment_info = response['payment']
        if payment_info['status'] == 'Credit':
            logger.info("Payment success %r", payment_info)
            transaction.settle()
        else:
            logger.info("Payment failed %r", payment_info)
            transaction.fail()

    def handle_transaction_response(self, transaction: Transaction, request):
        try:
            if request.GET.get('payment_id', None):
                transaction.data['payment_id'] = request.GET['payment_id']
                self.handle_transaction_response_inner(transaction, transaction.data['payment_id'])
            else:
                error = request.GET.get('err', None) or 'Unknown error'
                transaction.fail(fail_reason=error)
        except TransitionNotAllowed:
            pass

        transaction.save()


class InstamojoTriggered(InstamojoBase, TriggeredProcessorMixin):
    template_slug = 'instamojo_triggered'
    form_class = GenericTransactionForm

    def execute_transaction(self, transaction, request):
        """
        :param transaction: A Instamojo transaction in Initial or Pending state.
        :param transaction: The HTTP Request
        :return: True on success, False on failure.
        """

        # customer_details = transaction.payment_method.archived_customer
        
        customer = transaction.payment_method.customer

        instamojo_request = dict(
            redirect_url=request.build_absolute_uri(get_payment_complete_url(transaction, request)),
            buyer_name=customer.first_name,
            webhook=request.build_absolute_uri(
                reverse('instamojo-webhook', kwargs=dict(token=_get_jwt_token(transaction))))
        )

        try:
            instamojo_response = self.instamojo_wrapper.payment_request_create(
                'SpotDraft Subscription Charges', str(transaction.amount), **instamojo_request)
        except Exception as error:
            logger.error("Instamojo create request failed %r", error)
            transaction.fail(fail_reason=str(error))
            transaction.save()
            return False

        return self._parse_result(transaction, instamojo_response)

    def _parse_result(self, transaction: Transaction, result):
        if "success" in result and not result["success"]:
            transaction.fail(fail_reason=str(result["message"]))
            transaction.save()
            return False
        
        transaction.data['longurl'] = result['payment_request']['longurl']
        return True

        # elif "payment_request" in result:
        #     payment_request_obj = result["payment_request"]
        #     if payment_request_obj["status"] in ["Completed", "Pending"]:
        #         if payment_request_obj["status"] == "Completed":
        #             transaction.settle()
        #         else:
        #             transaction.process()
        #         transaction.save()
        #         return True                

        # return False
