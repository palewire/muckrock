"""
Custom QuerySets for the Task application
"""

from django.db import models
from django.db.models import Prefetch

from muckrock.communication.models import (
        EmailCommunication,
        )
from muckrock.foia.models import (
        FOIARequest,
        FOIACommunication,
        FOIAFile,
        )
from muckrock import task


class TaskQuerySet(models.QuerySet):
    """Object manager for all tasks"""
    def get_unresolved(self):
        """Get all unresolved tasks"""
        return self.filter(resolved=False)

    def get_resolved(self):
        """Get all resolved tasks"""
        return self.filter(resolved=True)

    def filter_by_foia(self, foia, user):
        """
        Get tasks that relate to the provided FOIA request.
        If user is staff, get all tasks.
        For all users, get new agency task.
        """
        # pylint:disable=no-self-use
        tasks = []
        # tasks that point to a communication
        communication_task_types = [
                task.models.ResponseTask,
                task.models.SnailMailTask,
                task.models.PortalTask,
                ]
        if user.is_staff:
            for task_type in communication_task_types:
                tasks += list(task_type.objects
                        .filter(communication__foia=foia)
                        .preload_list()
                        )
        # tasks that point to a foia
        foia_task_types = [
                task.models.FlaggedTask,
                task.models.StatusChangeTask,
                ]
        if user.is_staff:
            for task_type in foia_task_types:
                tasks += list(task_type.objects
                        .filter(foia=foia)
                        .preload_list()
                        )
        # tasks that point to an agency
        if foia.agency:
            tasks += list(task.models.NewAgencyTask.objects
                    .filter(agency=foia.agency)
                    .preload_list()
                    )
        if foia.agency and user.is_staff:
            tasks += list(task.models.ReviewAgencyTask.objects
                    .filter(agency=foia.agency)
                    .preload_list()
                    )
        return tasks


class OrphanTaskQuerySet(models.QuerySet):
    """Object manager for orphan tasks"""
    def get_from_domain(self, domain):
        """Get all orphan tasks from a specific domain"""
        return self.filter(communication__emails__from_email__email__icontains=domain)

    def preload_list(self):
        """Preloadrelations for list display"""
        return (self
                .select_related(
                    'communication__likely_foia__jurisdiction',
                    'resolved_by',
                    )
                .prefetch_related(
                    'communication__files',
                    Prefetch(
                        'communication__emails',
                        queryset=EmailCommunication.objects.select_related('from_email'),
                        )))


class SnailMailTaskQuerySet(models.QuerySet):
    """Object manager for snail mail tasks"""
    def preload_list(self):
        """Preload relations for list display"""
        from muckrock.agency.models import (
                AgencyEmail,
                AgencyPhone,
                AgencyAddress,
                )
        return (self
                .select_related(
                    'communication__foia__agency__portal',
                    'communication__foia__agency__appeal_agency__portal',
                    'communication__foia__user',
                    'communication__foia__jurisdiction',
                    'communication__foia__address',
                    'resolved_by',
                    )
                .prefetch_related(
                    'communication__files',
                    'communication__foia__communications',
                    'communication__emails',
                    'communication__faxes',
                    'communication__mails',
                    'communication__web_comms',
                    'communication__portals',
                    'communication__foia__communications__emails',
                    'communication__foia__communications__faxes',
                    'communication__foia__communications__mails',
                    'communication__foia__communications__web_comms',
                    'communication__foia__communications__portals',
                    Prefetch(
                        'communication__foia__communications',
                        queryset=FOIACommunication.objects.filter(response=True),
                        to_attr='ack'),
                    Prefetch('communication__foia__agency__agencyemail_set',
                        queryset=AgencyEmail.objects.select_related('email')),
                    Prefetch('communication__foia__agency__agencyphone_set',
                        queryset=AgencyPhone.objects.select_related('phone')),
                    Prefetch('communication__foia__agency__agencyaddress_set',
                        queryset=AgencyAddress.objects.select_related('address')),
                    Prefetch('communication__foia__agency__appeal_agency__agencyemail_set',
                        queryset=AgencyEmail.objects.select_related('email')),
                    Prefetch('communication__foia__agency__appeal_agency__agencyphone_set',
                        queryset=AgencyPhone.objects.select_related('phone')),
                    Prefetch('communication__foia__agency__appeal_agency__agencyaddress_set',
                        queryset=AgencyAddress.objects.select_related('address')),
                    ))


class StaleAgencyTaskQuerySet(models.QuerySet):
    """Object manager for stale agency tasks"""
    def preload_list(self):
        """Preload relations for list display"""
        return (self
                .select_related(
                    'agency__jurisdiction',
                    'resolved_by',
                    )
                .prefetch_related(
                    'agency__foiarequest_set__communications__foia__jurisdiction',
                    Prefetch('agency__foiarequest_set',
                        queryset=FOIARequest.objects.get_stale(),
                        to_attr='stale_requests_'),
                    ))


class FlaggedTaskQuerySet(models.QuerySet):
    """Object manager for flagged tasks"""
    def preload_list(self):
        """Preload relations for list display"""
        return self.select_related(
            'agency',
            'foia__jurisdiction',
            'jurisdiction',
            'user',
            'resolved_by',
            )


class ProjectReviewTaskQuerySet(models.QuerySet):
    """Object manager for project review tasks"""
    def preload_list(self):
        """Preload relations for list display"""
        return (self
                .select_related(
                    'project',
                    'resolved_by',
                    )
                .prefetch_related(
                    Prefetch(
                        'project__requests',
                        queryset=FOIARequest.objects.select_related('jurisdiction'),
                        ),
                    'project__articles',
                    'project__contributors',
                    ))


class NewAgencyTaskQuerySet(models.QuerySet):
    """Object manager for new agency tasks"""
    def preload_list(self):
        """Preload relations for list display"""
        from muckrock.agency.models import Agency
        return (self
                .select_related(
                    'agency__jurisdiction',
                    'resolved_by',
                    )
                .prefetch_related(
                    Prefetch('agency__foiarequest_set',
                        queryset=FOIARequest.objects.select_related('jurisdiction')),
                    Prefetch('agency__jurisdiction__agencies',
                        queryset=Agency.objects
                        .filter(status='approved')
                        .order_by('name'),
                        to_attr='other_agencies')))


class ReviewAgencyTaskQuerySet(models.QuerySet):
    """Object manager for review agency tasks"""
    def preload_list(self):
        """Preload relations for list display"""
        from muckrock.agency.models import (
                AgencyEmail,
                AgencyPhone,
                AgencyAddress,
                )
        return (self
                .select_related(
                    'agency__jurisdiction',
                    'agency__portal',
                    'resolved_by',
                    )
                .prefetch_related(
                    Prefetch('agency__agencyemail_set',
                        queryset=AgencyEmail.objects.select_related('email')),
                    Prefetch('agency__agencyphone_set',
                        queryset=AgencyPhone.objects.select_related('phone')),
                    Prefetch('agency__agencyaddress_set',
                        queryset=AgencyAddress.objects.select_related('address')),
                    ))

    def ensure_one_created(self, **kwargs):
        """Ensure exactly one model exists in the database as specified"""
        try:
            self.get_or_create(**kwargs)
        except task.models.ReviewAgencyTask.MultipleObjectsReturned:
            # if there are multiples, delete all but the first one
            # then try again
            to_delete = self.filter(**kwargs).order_by('date_created')[1:]
            self.filter(pk__in=to_delete).delete()
            self.ensure_one_created(**kwargs)


class ResponseTaskQuerySet(models.QuerySet):
    """Object manager for response tasks"""
    def preload_list(self):
        """Preload relations for list display"""
        return (self
                .select_related(
                    'communication__foia__agency',
                    'communication__foia__jurisdiction',
                    'resolved_by',
                    )
                .prefetch_related(
                    Prefetch('communication__files',
                        queryset=FOIAFile.objects.select_related('foia__jurisdiction')),
                    Prefetch('communication__foia__communications',
                        queryset=FOIACommunication.objects
                        .order_by('-date')
                        .prefetch_related(
                            'files',
                            'emails',
                            'faxes',
                            'mails',
                            'web_comms',
                            'portals',
                            ),
                        to_attr='reverse_communications'),
                    Prefetch('communication__emails',
                        queryset=EmailCommunication.objects.select_related('from_email')),
                    'communication__faxes',
                    'communication__mails',
                    'communication__web_comms',
                    'communication__portals',
                    ))


class StatusChangeTaskQuerySet(models.QuerySet):
    """Object manager for status change tasks"""
    def preload_list(self):
        """Preload relations for list display"""
        return self.select_related(
                'foia__jurisdiction',
                'user',
                'resolved_by',
                )


class CrowdfundTaskQuerySet(models.QuerySet):
    """Object manager for crowdfund tasks"""
    def preload_list(self):
        """Preload relations for list display"""
        return self.select_related(
                'crowdfund__foia__jurisdiction',
                'resolved_by',
                )


class MultiRequestTaskQuerySet(models.QuerySet):
    """Object manager for multirequest tasks"""
    def preload_list(self):
        """Preload relations for list display"""
        return (self
                .select_related(
                    'multirequest__user',
                    'resolved_by',
                    )
                .prefetch_related('multirequest__agencies')
                )


class NewExemptionTaskQuerySet(models.QuerySet):
    """Object manager for new exemption tasks"""
    def preload_list(self):
        """Preload relations for list display"""
        return self.select_related(
                'foia__agency__jurisdiction__parent',
                'foia__jurisdiction__parent',
                'user',
                'resolved_by',
                )


class PortalTaskQuerySet(models.QuerySet):
    """Object manager for portal tasks"""
    def preload_list(self):
        """Preload relations for list display"""
        return (self
                .select_related(
                    'communication__foia__agency',
                    'communication__foia__jurisdiction',
                    'communication__foia__user',
                    'communication__foia__portal',
                    'communication__from_user__profile',
                    'resolved_by',
                    )
                .prefetch_related(
                    Prefetch(
                        'communication__foia__communications',
                        queryset=FOIACommunication.objects.filter(response=True),
                        to_attr='has_ack'),
                    Prefetch('communication__foia__communications',
                        queryset=FOIACommunication.objects
                        .order_by('-date')
                        .select_related(
                            'from_user__profile',
                            )
                        .prefetch_related(
                            'files',
                            'emails',
                            'faxes',
                            'mails',
                            'web_comms',
                            'portals',
                            ),
                        to_attr='reverse_communications'),
                    'communication__files',
                    'communication__emails',
                    'communication__faxes',
                    'communication__mails',
                    'communication__web_comms',
                    'communication__portals',
                    ))
