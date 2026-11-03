"""Shared vocabulary for review-first background agent proposals."""
ACTIONS=('tag','assign','note','draft_reply','task')


def allowed_actions(agent):
    return agent.get('allowed_actions',list(ACTIONS))


def validate_actions(values):
    if not isinstance(values,list) or len(values)>len(ACTIONS) or any(not isinstance(value,str) or value not in ACTIONS for value in values):raise ValueError('Choose supported agent proposal actions, or none for information only.')
    return list(dict.fromkeys(values))
