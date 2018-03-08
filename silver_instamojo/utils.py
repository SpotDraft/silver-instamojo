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

import hmac
import hashlib

from django.http import Http404


def verify_instamojo_hmac(data: dict, salt: str) -> bool:
    data = data.copy()
    mac_provided = data.pop('mac')[0]
    message = "|".join(v for k, v in sorted(data.items(), key=lambda x: x[0].lower()))
    # Pass the 'salt' without the <>.
    mac_calculated = hmac.new(str.encode(salt), str.encode(message), hashlib.sha1).hexdigest()
    if mac_provided == mac_calculated:
        return True
        # if data['status'] == "Credit":
        #     # Payment was successful, mark it as completed in your database.
        # else:
        #     # Payment was unsuccessful, mark it as failed in your database.
        # self.send_response(200)
    else:
        raise Http404