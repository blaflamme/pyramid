import unittest

from repoze.bfg.testing import cleanUp

class TestACLAuthorizationPolicy(unittest.TestCase):
    def setUp(self):
        cleanUp()

    def tearDown(self):
        cleanUp()

    def _getTargetClass(self):
        from repoze.bfg.authorization import ACLAuthorizationPolicy
        return ACLAuthorizationPolicy

    def _makeOne(self):
        return self._getTargetClass()()

    def test_class_implements_IAuthorizationPolicy(self):
        from zope.interface.verify import verifyClass
        from repoze.bfg.interfaces import IAuthorizationPolicy
        verifyClass(IAuthorizationPolicy, self._getTargetClass())

    def test_instance_implements_IAuthorizationPolicy(self):
        from zope.interface.verify import verifyObject
        from repoze.bfg.interfaces import IAuthorizationPolicy
        verifyObject(IAuthorizationPolicy, self._makeOne())

    def test_permits_no_acl(self):
        context = DummyContext()
        policy = self._makeOne()
        self.assertEqual(policy.permits(context, [], 'view'), False)
        
    def test_permits(self):
        from repoze.bfg.security import Deny
        from repoze.bfg.security import Allow
        from repoze.bfg.security import Everyone
        from repoze.bfg.security import Authenticated
        from repoze.bfg.security import ALL_PERMISSIONS
        from repoze.bfg.security import DENY_ALL
        root = DummyContext()
        community = DummyContext(__name__='community', __parent__=root)
        blog = DummyContext(__name__='blog', __parent__=community)
        root.__acl__ = [
            (Allow, Authenticated, VIEW),
            ]
        community.__acl__ = [
            (Allow, 'fred', ALL_PERMISSIONS),
            (Allow, 'wilma', VIEW),
            DENY_ALL,
            ]
        blog.__acl__ = [
            (Allow, 'barney', MEMBER_PERMS),
            (Allow, 'wilma', VIEW),
            ]

        policy = self._makeOne()

        result = policy.permits(blog, [Everyone, Authenticated, 'wilma'],
                                'view')
        self.assertEqual(result, True)
        self.assertEqual(result.context, blog)
        self.assertEqual(result.ace, (Allow, 'wilma', VIEW))

        result = policy.permits(blog, [Everyone, Authenticated, 'wilma'],
                                'delete')
        self.assertEqual(result, False)
        self.assertEqual(result.context, community)
        self.assertEqual(result.ace, (Deny, Everyone, ALL_PERMISSIONS))

        result = policy.permits(blog, [Everyone, Authenticated, 'fred'], 'view')
        self.assertEqual(result, True)
        self.assertEqual(result.context, community)
        self.assertEqual(result.ace, (Allow, 'fred', ALL_PERMISSIONS))
        result = policy.permits(blog, [Everyone, Authenticated, 'fred'],
                                'doesntevenexistyet')
        self.assertEqual(result, True)
        self.assertEqual(result.context, community)
        self.assertEqual(result.ace, (Allow, 'fred', ALL_PERMISSIONS))

        result = policy.permits(blog, [Everyone, Authenticated, 'barney'],
                                'view')
        self.assertEqual(result, True)
        self.assertEqual(result.context, blog)
        self.assertEqual(result.ace, (Allow, 'barney', MEMBER_PERMS))
        result = policy.permits(blog, [Everyone, Authenticated, 'barney'],
                                'administer')
        self.assertEqual(result, False)
        self.assertEqual(result.context, community)
        self.assertEqual(result.ace, (Deny, Everyone, ALL_PERMISSIONS))
        
        result = policy.permits(root, [Everyone, Authenticated, 'someguy'],
                                'view')
        self.assertEqual(result, True)
        self.assertEqual(result.context, root)
        self.assertEqual(result.ace, (Allow, Authenticated, VIEW))
        result = policy.permits(blog,
                                [Everyone, Authenticated, 'someguy'], 'view')
        self.assertEqual(result, False)
        self.assertEqual(result.context, community)
        self.assertEqual(result.ace, (Deny, Everyone, ALL_PERMISSIONS))

        result = policy.permits(root, [Everyone], 'view')
        self.assertEqual(result, False)
        self.assertEqual(result.context, root)
        self.assertEqual(result.ace, None)

        context = DummyContext()
        result = policy.permits(context, [Everyone], 'view')
        self.assertEqual(result, False)

    def test_principals_allowed_by_permission_direct(self):
        from repoze.bfg.security import Allow
        from repoze.bfg.security import DENY_ALL
        context = DummyContext()
        acl = [ (Allow, 'chrism', ('read', 'write')),
                DENY_ALL,
                (Allow, 'other', 'read') ]
        context.__acl__ = acl
        policy = self._makeOne()
        result = sorted(
            policy.principals_allowed_by_permission(context, 'read'))
        self.assertEqual(result, ['chrism'])

    def test_principals_allowed_by_permission(self):
        from repoze.bfg.security import Allow
        from repoze.bfg.security import Deny
        from repoze.bfg.security import DENY_ALL
        from repoze.bfg.security import ALL_PERMISSIONS
        root = DummyContext(__name__='', __parent__=None)
        community = DummyContext(__name__='community', __parent__=root)
        blog = DummyContext(__name__='blog', __parent__=community)
        root.__acl__ = [ (Allow, 'chrism', ('read', 'write')),
                         (Allow, 'other', ('read',)),
                         (Allow, 'jim', ALL_PERMISSIONS)]
        community.__acl__ = [  (Deny, 'flooz', 'read'),
                               (Allow, 'flooz', 'read'),
                               (Allow, 'mork', 'read'),
                               (Deny, 'jim', 'read'),
                               (Allow, 'someguy', 'manage')]
        blog.__acl__ = [ (Allow, 'fred', 'read'),
                         DENY_ALL]

        policy = self._makeOne()
        
        result = sorted(policy.principals_allowed_by_permission(blog, 'read'))
        self.assertEqual(result, ['fred'])
        result = sorted(policy.principals_allowed_by_permission(community,
            'read'))
        self.assertEqual(result, ['chrism', 'mork', 'other'])
        result = sorted(policy.principals_allowed_by_permission(community,
            'read'))
        result = sorted(policy.principals_allowed_by_permission(root, 'read'))
        self.assertEqual(result, ['chrism', 'jim', 'other'])

    def test_principals_allowed_by_permission_no_acls(self):
        context = DummyContext()
        policy = self._makeOne()
        result = sorted(policy.principals_allowed_by_permission(context,'read'))
        self.assertEqual(result, [])

class DummyContext:
    def __init__(self, *arg, **kw):
        self.__dict__.update(kw)


VIEW = 'view'
EDIT = 'edit'
CREATE = 'create'
DELETE = 'delete'
MODERATE = 'moderate'
ADMINISTER = 'administer'
COMMENT = 'comment'

GUEST_PERMS = (VIEW, COMMENT)
MEMBER_PERMS = GUEST_PERMS + (EDIT, CREATE, DELETE)
MODERATOR_PERMS = MEMBER_PERMS + (MODERATE,)
ADMINISTRATOR_PERMS = MODERATOR_PERMS + (ADMINISTER,)
