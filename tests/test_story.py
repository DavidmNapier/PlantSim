from demo import config
from demo.story import chapters as S


def test_chapters_back_to_back():
    chs = S.chapters()
    assert len(chs) == 7 and chs[0][2] == 1
    for a, b in zip(chs, chs[1:]):
        assert b[2] == a[3] + 1
    secs = sum(c[1] for c in config.STORY)
    assert 6 * 60 <= secs <= 7.5 * 60          # about 7 minutes
    assert S.total_frames() == secs * config.STORY_FPS


def test_minute_mapping_within_chapters():
    for i, _, f0, f1, m0, m1, _ in S.chapters():
        assert abs(S.minute_at(f0) - m0) < 1e-9 and abs(S.minute_at(f1) - m1) < 1e-9
        assert S.chapter_at(f0)[0] == i and S.chapter_at(f1)[0] == i
        mids = [S.minute_at(f) for f in range(f0, f1 + 1, 50)]
        assert mids == sorted(mids)
        assert 0 <= m0 < m1 <= config.TIMELINE_END_MIN


def test_story_covers_the_fault_and_yard():
    chs = {c[0]: c for c in S.chapters()}
    p0, p1 = config.FAULT_SCHEDULE[1][:2]
    assert chs[3][4] <= p0 and chs[3][5] >= p1                   # live chapter spans the scripted pulse
    assert chs[4][5] >= config.SIM_MINUTES                        # pile finished in ch4
    assert chs[5][4] <= config.STOCKPILE["reclaim_start_min"]     # reclaim starts in ch5
