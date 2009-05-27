from zope.interface import implements

from repoze.bfg.interfaces import IAuthorizationPolicy
from repoze.bfg.location import lineage
from repoze.bfg.security import Allow
from repoze.bfg.security import Deny
from repoze.bfg.security import ACLAllowed
from repoze.bfg.security import ACLDenied
from repoze.bfg.security import Everyone

class ACLAuthorizationPolicy(object):
    """ An authorization policy which uses ACLs in the following ways:

    - When checking whether a user is permitted (via the ``permits``
      method), the security policy consults the ``context`` for an ACL
      first.  If no ACL exists on the context, or one does exist but
      the ACL does not explicitly allow or deny access for any of the
      effective principals, consult the context's parent ACL, and so
      on, until the lineage is exhausted or we determine that the
      policy permits or denies.

      During this processing, if any ``Deny`` ACE is found matching
      any principal in ``principals``, stop processing by returning an
      ``ACLDenied`` (equals False) immediately.  If any ``Allow`` ACE
      is found matching any principal, stop processing by returning an
      ``ACLAllowed`` (equals True) immediately.  If we exhaust the
      context's lineage, and no ACE has explicitly permitted or denied
      access, return an ``ACLDenied``.  This differs from the
      non-inheriting security policy (the ``ACLSecurityPolicy``) by
      virtue of the fact that it does not stop looking for ACLs in the
      object lineage after it finds the first one.

    - When computing principals allowed by a permission via the
      ``principals_allowed_by_permission`` method, we compute the set
      of principals that are explicitly granted the ``permission`` in
      the provided ``context``.  We do this by walking 'up' the object
      graph *from the root* to the context.  During this walking
      process, if we find an explicit ``Allow`` ACE for a principal
      that matches the ``permission``, the principal is included in
      the allow list.  However, if later in the walking process that
      user is mentioned in any ``Deny`` ACE for the permission, the
      user is removed from the allow list.  If a ``Deny`` to the
      principal ``Everyone`` is encountered during the walking process
      that matches the ``permission``, the allow list is cleared for
      all principals encountered in previous ACLs.  The walking
      process ends after we've processed the any ACL directly attached
      to ``context``; a set of principals is returned.
    """

    implements(IAuthorizationPolicy)

    def permits(self, context, principals, permission):
        """ Return ``ACLAllowed`` if the policy permits access,
        ``ACLDenied`` if not. """
        
        for location in lineage(context):
            try:
                acl = location.__acl__
            except AttributeError:
                continue

            for ace in acl:
                ace_action, ace_principal, ace_permissions = ace
                if ace_principal in principals:
                    if not hasattr(ace_permissions, '__iter__'):
                        ace_permissions = [ace_permissions]
                    if permission in ace_permissions:
                        if ace_action == Allow:
                            return ACLAllowed(ace, acl, permission,
                                              principals, location)
                        else:
                            return ACLDenied(ace, acl, permission,
                                             principals, location)

        # default deny if no ACL in lineage at all
        return ACLDenied(None, None, permission, principals, context)

    def principals_allowed_by_permission(self, context, permission):
        """ Return the set of principals explicitly granted the
        permission named ``permission`` according to the ACL directly
        attached to the context context as well as inherited ACLs. """
        allowed = set()

        for location in reversed(list(lineage(context))):
            # NB: we're walking *up* the object graph from the root
            try:
                acl = location.__acl__
            except AttributeError:
                continue

            allowed_here = set()
            denied_here = set()
            
            for ace_action, ace_principal, ace_permissions in acl:
                if not hasattr(ace_permissions, '__iter__'):
                    ace_permissions = [ace_permissions]
                if ace_action == Allow and permission in ace_permissions:
                    if not ace_principal in denied_here:
                        allowed_here.add(ace_principal)
                if ace_action == Deny and permission in ace_permissions:
                    denied_here.add(ace_principal)
                    if ace_principal == Everyone:
                        # clear the entire allowed set, as we've hit a
                        # deny of Everyone ala (Deny, Everyone, ALL)
                        allowed = set()
                        break
                    elif ace_principal in allowed:
                        allowed.remove(ace_principal)

            allowed.update(allowed_here)

        return allowed