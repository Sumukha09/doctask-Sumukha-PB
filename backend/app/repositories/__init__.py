"""Repository layer.

Repositories translate between SQLAlchemy and the domain model. They must not
orchestrate workflows or call external services; those concerns live in the
service layer. Concrete repositories are added in later steps.
"""
