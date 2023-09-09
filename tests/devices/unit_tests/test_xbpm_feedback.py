import pytest
from ophyd.sim import make_fake_device

from dodal.devices.xbpm_feedback import XBPMFeedback


@pytest.fixture
def fake_xbpm_feedback():
    FakeXBPMFeedback = make_fake_device(XBPMFeedback)
    return FakeXBPMFeedback(name="xbpm")


@pytest.mark.skip()
def test_given_pos_ok_when_xbpm_feedback_kickoff_then_return_immediately(
    fake_xbpm_feedback: XBPMFeedback,
):
    fake_xbpm_feedback.pos_ok.sim_put(1)
    status = fake_xbpm_feedback.trigger()
    status.wait(0.1)
    assert status.done and status.success


@pytest.mark.skip()
def test_given_pos_not_ok_and_goes_ok_for_stability_time_when_xbpm_feedback_kickoff_then_return_immediately(
    fake_xbpm_feedback: XBPMFeedback,
):
    fake_xbpm_feedback.STABILITY_TIME = 0.1
    fake_xbpm_feedback.pos_ok.sim_put(0)
    status = fake_xbpm_feedback.trigger()

    assert not status.done

    fake_xbpm_feedback.pos_ok.sim_put(1)
    status.wait(0.2)
    assert status.done and status.success
