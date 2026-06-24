import pytest
from datetime import datetime, timezone
import json
from backend.modules.application_tracker import ApplicationTracker
from backend.models.application import Application

@pytest.mark.asyncio
async def test_classify_response_mock():
    tracker = ApplicationTracker()
    
                    
    status, reason = await tracker.classify_response("We would like to invite you for an interview on Monday.")
    assert status == "Interview"
    
                     
    status, reason = await tracker.classify_response("Please complete this hackerrank assessment before Friday.")
    assert status == "Assessment"
    
                   
    status, reason = await tracker.classify_response("Unfortunately we will not be moving forward with your application.")
    assert status == "Rejected"
    
                
    status, reason = await tracker.classify_response("We are thrilled to offer you the position.")
    assert status == "Offer"

@pytest.mark.asyncio
async def test_monitor_application_updates_status():
    tracker = ApplicationTracker()
    
                                                                  
    async def mock_check(thread_id, date):
        return "Unfortunately, we decided to go with another candidate due to a profile mismatch."
        
    tracker.check_thread_for_replies = mock_check
    
    app = Application(
        id="test-1",
        thread_id="thread-xyz",
        status="applied",
        applied_at=datetime.now(timezone.utc).replace(tzinfo=None)
    )
    
    changed = await tracker.monitor_application(app)
    
    assert changed is True
    assert app.status == "Rejected"
    assert app.rejection_reason == "Profile mismatch"
