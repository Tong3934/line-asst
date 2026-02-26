"""handlers — one module per conversation topic.

State is the exclusive routing key; handlers never branch on other session fields
to decide the next action (per tech-spec §7.1, §7.2).
"""
