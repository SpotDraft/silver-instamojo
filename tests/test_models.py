import pytest
from faker import Faker
from mock import MagicMock, patch
from django_dynamic_fixture import G

from django.utils.dateparse import parse_datetime

from silver.models import Transaction, PaymentMethod
from silver_instamojo.forms import InstamojoBillingForm, InstamojoTransactionFormBase
from silver_instamojo.models import InstamojoPaymentMethod
from silver_instamojo.payment_processors import instamojo_ipn_received, instamojo_token_received

from .fixtures import (customer, transaction, transaction_triggered,
                       payment_method, proforma, invoice,
                       payment_processor, payment_processor_triggered)

faker = Faker()


def test_payment_method_data_set():
    payment_method = InstamojoPaymentMethod()

    payment_method.decrypt_data = lambda value: value
    payment_method.encrypt_data = lambda value: value

    payment_method.token = "random token"
    assert payment_method.token == "random token"

    payment_method.archived_customer = {'name': 'test'}
    assert payment_method.archived_customer == {'name': 'test'}


@pytest.mark.django_db
@pytest.mark.parametrize('data, form_class, archived_customer', [
    ({
        'email': faker.email(),
        'first_name': faker.first_name(),
        'last_name': faker.last_name(),
        'phone': faker.phone_number(),
        'country': '',
        'fiscal_code': ''
    }, InstamojoBillingForm, {}),
    ({
        'email': 'john@acme.com',
        'first_name': 'John',
        'last_name': 'Doe',
        'phone': '+40000000000',
        'country': 'RO',
        'city': 'Timisoara',
        'fiscal_code': ''
    }, InstamojoTransactionFormBase, {
        'BILL_ADDRESS': '9 9',
        'BILL_CITY': 'Timisoara',
        'BILL_COUNTRYCODE': 'RO',
        'BILL_EMAIL': 'john@acme.com',
        'BILL_FNAME': 'John',
        'BILL_LNAME': 'Doe',
        'BILL_PHONE': '+40000000000'
    })
])
def test_payment_processor_get_form(payment_processor, transaction, data,
                                    form_class, archived_customer):
    form = payment_processor.get_form(transaction, MagicMock(POST=data))

    assert isinstance(form, form_class)
    assert transaction.payment_method.archived_customer == archived_customer


@pytest.mark.django_db
def test_execute_transaction_wrong_payment_processor(payment_processor_triggered,
                                                     transaction_triggered):
    assert not payment_processor_triggered.execute_transaction(transaction_triggered)


@pytest.mark.django_db
def test_execute_transaction_wrong_transaction_state(payment_processor_triggered):
    payment_processor_triggered._charge_transaction = lambda x: True

    transaction_triggered = MagicMock(payment_processor=payment_processor_triggered,
                                      state=Transaction.States.Settled)
    assert not payment_processor_triggered.execute_transaction(transaction_triggered)


@pytest.mark.django_db
def test_execute_transaction_happy_path(payment_processor_triggered):
    payment_processor_triggered._charge_transaction = lambda x: True

    transaction_triggered = MagicMock(payment_processor=payment_processor_triggered,
                                      state=Transaction.States.Pending)
    assert payment_processor_triggered.execute_transaction(transaction_triggered)


@pytest.mark.django_db
@patch('silver_instamojo.payment_processors.TokenPayment')
def test_charge_transaction_triggered(mocked_token_payment,
                                      payment_processor_triggered,
                                      payment_method, transaction_triggered):
    mocked_token_payment.return_value.pay.return_value = '{"code": "0"}'

    payment_method.token = faker.word()
    payment_method.archived_customer = {
        "BILL_ADDRESS": faker.address(),
        "BILL_CITY": faker.city(),
        "BILL_EMAIL": faker.email(),
        "BILL_FNAME": faker.first_name(),
        "BILL_LNAME": faker.last_name(),
        "BILL_PHONE": faker.phone_number(),
    }

    assert payment_processor_triggered._charge_transaction(transaction_triggered)

    asserted_payment_details = payment_method.archived_customer
    asserted_payment_details.update({
        "DELIVERY_ADDRESS": asserted_payment_details["BILL_ADDRESS"],
        "DELIVERY_CITY": asserted_payment_details["BILL_CITY"],
        "DELIVERY_EMAIL": asserted_payment_details["BILL_EMAIL"],
        "DELIVERY_FNAME": asserted_payment_details["BILL_FNAME"],
        "DELIVERY_LNAME": asserted_payment_details["BILL_LNAME"],
        "DELIVERY_PHONE": asserted_payment_details["BILL_PHONE"],
        "AMOUNT": str(transaction_triggered.amount),
        "CURRENCY": str(transaction_triggered.currency),
        "EXTERNAL_REF": str(transaction_triggered.uuid),
    })

    mocked_token_payment.assert_called_once_with(asserted_payment_details,
                                                 payment_method.token)


@pytest.mark.django_db
@pytest.mark.parametrize('payment_result, excepted_return', [
    ('{"code": "0"}', True),
    ('{"code": "1"}', False),
    ('{code: "1"}', False),
])
def test_parse_token_payment_result(payment_processor_triggered,
                                    transaction_triggered, payment_result,
                                    excepted_return):
    assert payment_processor_triggered._parse_result(transaction_triggered,
                                                     payment_result) == excepted_return


@pytest.mark.django_db
@patch('silver.models.transactions.transaction.Transaction.update_document_state')
def test_ipn_received(mocked_document, transaction):
    instamojo_ipn_received(MagicMock(REFNOEXT=transaction.uuid))

    transaction.refresh_from_db()

    assert transaction.state == "settled"


@pytest.mark.django_db
def test_token_received(transaction_triggered):
    sender = MagicMock(ipn=MagicMock(REFNOEXT=transaction_triggered.uuid),
                       IPN_CC_TOKEN=faker.word(), IPN_CC_EXP_DATE='2017-07-31',
                       IPN_CC_MASK=faker.word())
    instamojo_token_received(sender)

    transaction_triggered.payment_method.refresh_from_db()

    expected_valid_until = parse_datetime(sender.IPN_CC_EXP_DATE + " 00:00:00")
    assert transaction_triggered.payment_method.valid_until == expected_valid_until
    assert transaction_triggered.payment_method.token == sender.IPN_CC_TOKEN
    assert transaction_triggered.payment_method.display_info == sender.IPN_CC_MASK
    assert transaction_triggered.payment_method.verified
