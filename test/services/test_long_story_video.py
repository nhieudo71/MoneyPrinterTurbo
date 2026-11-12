import json
from unittest.mock import patch

from app.models.schema import TaskVideoRequest, VideoParams, VideoScriptRequest
from app.services import llm


def test_estimate_story_plan_presets():
    for minutes, expected_min_chapters in [(5, 2), (10, 4), (15, 5), (20, 7), (30, 10)]:
        words, chapters = llm.estimate_story_plan(minutes)
        assert words == minutes * llm.STORYTELLING_WORDS_PER_MINUTE
        assert chapters == expected_min_chapters

    assert llm.estimate_story_plan(0) == (0, 1)


def test_schema_accepts_long_story_params():
    params = VideoParams(
        video_subject="Truyện đêm khuya bên tách trà ấm",
        target_duration_minutes=30,
        story_mode=True,
        video_clip_duration=30,
    )
    assert params.target_duration_minutes == 30
    assert params.story_mode is True
    assert params.video_clip_duration == 30

    req = TaskVideoRequest(
        video_subject="Kể chuyện đêm khuya",
        target_duration_minutes=15,
        story_mode=True,
        video_clip_duration=30,
    )
    assert req.target_duration_minutes == 15
    assert req.story_mode is True
    assert req.video_clip_duration == 30

    script_req = VideoScriptRequest(
        video_subject="Kể chuyện đêm khuya",
        target_duration_minutes=20,
        story_mode=True,
    )
    assert script_req.target_duration_minutes == 20
    assert script_req.story_mode is True


def test_generate_long_story_script_builds_outline_and_chapters():
    outline = [
        "Đêm mưa yên tĩnh ở thị trấn nhỏ",
        "Cuộc gặp gỡ bất ngờ dưới mái hiên",
        "Ký ức xưa ùa về bên bếp lửa",
        "Lời tạm biệt dịu dàng trước bình minh",
    ]
    calls = []

    def fake_generate_response(prompt, app_config=None):
        calls.append(prompt)
        if len(calls) == 1:
            return json.dumps(outline, ensure_ascii=False)
        chapter_idx = len(calls) - 1
        return f"Nội dung chương {chapter_idx} kể tiếp câu chuyện đêm khuya thật êm dịu."

    with patch("app.services.llm._generate_response", side_effect=fake_generate_response):
        result = llm.generate_script(
            video_subject="Đêm mưa bên hiên nhà",
            language="vi-VN",
            target_duration_minutes=10,
            story_mode=True,
        )

    assert len(calls) == 5  # 1 outline call + 4 chapter calls
    for idx in range(1, 5):
        assert f"Nội dung chương {idx}" in result
    # Chapter 2 prompt should include Chapter 1's tail for continuity
    assert "Nội dung chương 1" in calls[2]


def test_generate_short_script_with_story_mode_uses_storytelling_prompt():
    captured_prompts = []

    def fake_generate_response(prompt, app_config=None):
        captured_prompts.append(prompt)
        return "Một câu chuyện ngắn nhẹ nhàng giữa đêm khuya tĩnh lặng."

    with patch("app.services.llm._generate_response", side_effect=fake_generate_response):
        result = llm.generate_script(
            video_subject="Ngọn đèn dầu cũ",
            language="vi-VN",
            paragraph_number=2,
            target_duration_minutes=0,
            story_mode=True,
        )

    assert "Late-Night Storyteller" in captured_prompts[0]
    assert "Ngọn đèn dầu cũ" in result or "câu chuyện ngắn" in result
