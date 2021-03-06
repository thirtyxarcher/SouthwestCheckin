import checkin
import json
import pytest
import requests
from datetime import datetime, timedelta
from pytz import timezone, utc
from tzlocal import get_localzone

def template_time(file_name):
    in_string = open(file_name, 'r').read()
    t = datetime.now() + timedelta(seconds=5)
    in_string = in_string.replace('DATE_HERE', t.strftime('%Y-%m-%d'))
    in_string = in_string.replace('TIME_HERE', t.strftime('%H:%M'))
    return in_string

def test_checkin(requests_mock):
    requests_mock.register_uri('GET', '/api/mobile-misc/v1/mobile-misc/page/view-reservation/XXXX?first-name=John&last-name=Smith', text=template_time('fixtures/view-reservation.json'))
    requests_mock.register_uri('GET', '/api/mobile-air-operations/v1/mobile-air-operations/page/check-in/XXXX?first-name=John&last-name=Smith', text=template_time('fixtures/checkin-get.json'))
    requests_mock.register_uri('POST', '/api/mobile-air-operations/v1/mobile-air-operations/page/check-in', text=template_time('fixtures/checkin-post.json'))
    requests_mock.register_uri('POST', '/php/apsearch.php', text=template_time('fixtures/openflights.json'))
    try:
        checkin.auto_checkin('XXXX', 'John', 'Smith', None, None)
    except:
        pytest.fail("Error checking in")

def test_timezone_localization():
    tz = timezone('America/Los_Angeles')
    date = tz.localize(datetime.strptime('2018-01-01 13:00', '%Y-%m-%d %H:%M'))
    assert date.strftime('%z') == '-0800'

def test_openflights_api():
    tzrequest = {'iata': 'LAX',
                 'country': 'ALL',
                 'db': 'airports',
                 'iatafilter': 'true',
                 'action': 'SEARCH',
                 'offset': '0'}
    tzresult = requests.post("https://openflights.org/php/apsearch.php", tzrequest)
    airport_tz = timezone(json.loads(tzresult.text)['airports'][0]['tz_id'])
    assert airport_tz.zone == "America/Los_Angeles"

def test_notifications(requests_mock, mocker):
    requests_mock.register_uri('GET', '/api/mobile-air-operations/v1/mobile-air-operations/page/check-in/XXXX?first-name=John&last-name=Smith', text=template_time('fixtures/checkin-get.json'))
    data = template_time('fixtures/checkin-post.json')
    requests_mock.register_uri('POST', '/api/mobile-air-operations/v1/mobile-air-operations/page/check-in', text=data)
    data = json.loads(data)
    requests_mock.register_uri('POST', '/php/apsearch.php', text=template_time('fixtures/openflights.json'))
    mocked_checkin = mocker.patch('checkin.send_notification')
    t = datetime.now(utc).astimezone(get_localzone()) + timedelta(minutes=5)

    try:
        checkin.schedule_checkin(t, 'XXXX', 'John', 'Smith', None, None)
        checkin.send_notification.assert_not_called()
        checkin.schedule_checkin(t, 'XXXX', 'John', 'Smith', 'test@example.com', None)
        checkin.send_notification.assert_called_once_with(data['checkInConfirmationPage'], emailaddr='test@example.com')
        checkin.send_notification.reset_mock()
        checkin.schedule_checkin(t, 'XXXX', 'John', 'Smith', None, '1234567890')
        checkin.send_notification.assert_called_once_with(data['checkInConfirmationPage'], mobilenum='1234567890')
    except:
        pytest.fail("Error checking in")
