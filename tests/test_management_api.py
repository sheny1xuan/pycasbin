from functools import partial

import casbin
from tests.test_enforcer import get_examples, TestCaseBase


class TestManagementApi(TestCaseBase):
    def get_enforcer(self, model=None, adapter=None):
        return casbin.Enforcer(
            model,
            adapter,
        )

    def test_get_list(self):
        e = self.get_enforcer(
            get_examples("rbac_model.conf"),
            get_examples("rbac_policy.csv"),
            # True,
        )

        self.assertEqual(e.get_all_subjects(), ["alice", "bob", "data2_admin"])
        self.assertEqual(e.get_all_objects(), ["data1", "data2"])
        self.assertEqual(e.get_all_actions(), ["read", "write"])
        self.assertEqual(e.get_all_roles(), ["data2_admin"])

    def test_get_policy_api(self):
        e = self.get_enforcer(
            get_examples("rbac_model.conf"),
            get_examples("rbac_policy.csv"),
        )
        self.assertEqual(
            e.get_policy(),
            [
                ["alice", "data1", "read"],
                ["bob", "data2", "write"],
                ["data2_admin", "data2", "read"],
                ["data2_admin", "data2", "write"],
            ],
        )

        self.assertEqual(
            e.get_filtered_policy(0, "alice"), [["alice", "data1", "read"]]
        )
        self.assertEqual(e.get_filtered_policy(0, "bob"), [["bob", "data2", "write"]])
        self.assertEqual(
            e.get_filtered_policy(0, "data2_admin"),
            [["data2_admin", "data2", "read"], ["data2_admin", "data2", "write"]],
        )
        self.assertEqual(
            e.get_filtered_policy(1, "data1"), [["alice", "data1", "read"]]
        )
        self.assertEqual(
            e.get_filtered_policy(1, "data2"),
            [
                ["bob", "data2", "write"],
                ["data2_admin", "data2", "read"],
                ["data2_admin", "data2", "write"],
            ],
        )
        self.assertEqual(
            e.get_filtered_policy(2, "read"),
            [["alice", "data1", "read"], ["data2_admin", "data2", "read"]],
        )
        self.assertEqual(
            e.get_filtered_policy(2, "write"),
            [["bob", "data2", "write"], ["data2_admin", "data2", "write"]],
        )
        self.assertEqual(
            e.get_filtered_policy(0, "data2_admin", "data2"),
            [["data2_admin", "data2", "read"], ["data2_admin", "data2", "write"]],
        )

        # Note: "" (empty string) in fieldValues means matching all values.
        self.assertEqual(
            e.get_filtered_policy(0, "data2_admin", "", "read"),
            [["data2_admin", "data2", "read"]],
        )
        self.assertEqual(
            e.get_filtered_policy(1, "data2", "write"),
            [["bob", "data2", "write"], ["data2_admin", "data2", "write"]],
        )

        self.assertTrue(e.has_policy(["alice", "data1", "read"]))
        self.assertTrue(e.has_policy(["bob", "data2", "write"]))
        self.assertFalse(e.has_policy(["alice", "data2", "read"]))
        self.assertFalse(e.has_policy(["bob", "data3", "write"]))
        self.assertEqual(e.get_grouping_policy(), [["alice", "data2_admin"]])
        self.assertEqual(
            e.get_filtered_grouping_policy(0, "alice"), [["alice", "data2_admin"]]
        )
        self.assertEqual(e.get_filtered_grouping_policy(0, "bob"), [])
        self.assertEqual(e.get_filtered_grouping_policy(1, "data1_admin"), [])
        self.assertEqual(
            e.get_filtered_grouping_policy(1, "data2_admin"), [["alice", "data2_admin"]]
        )
        # Note: "" (empty string) in fieldValues means matching all values.
        self.assertEqual(
            e.get_filtered_grouping_policy(0, "", "data2_admin"),
            [["alice", "data2_admin"]],
        )
        self.assertTrue(e.has_grouping_policy(["alice", "data2_admin"]))
        self.assertFalse(e.has_grouping_policy(["bob", "data2_admin"]))

    def test_get_policy_matching_function(self):
        e = self.get_enforcer(
            get_examples("rbac_with_domain_and_policy_pattern_model.conf"),
            get_examples("rbac_with_domain_and_policy_pattern_policy.csv"),
        )

        self.assertEqual(
            e.get_policy(),
            [
                ["admin", "domain.*", "data1", "read"],
                ["user", "domain.*", "data3", "read"],
                ["user", "domain.1", "data2", "read"],
                ["user", "domain.1", "data2", "write"],
            ],
        )

        km2_fn = casbin.util.key_match2_func
        self.assertEqual(
            e.get_filtered_grouping_policy(2, partial(km2_fn, "domain.3")),
            [["alice", "user", "*"], ["bob", "admin", "domain.3"]],
        )

        self.assertEqual(
            e.get_filtered_grouping_policy(2, partial(km2_fn, "domain.1")),
            [["alice", "user", "*"]],
        )

        # first and second p record matches to domain.3
        self.assertEqual(
            e.get_filtered_policy(1, partial(km2_fn, "domain.3")),
            [
                ["admin", "domain.*", "data1", "read"],
                ["user", "domain.*", "data3", "read"],
            ],
        )

        self.assertEqual(
            sorted(e.get_filtered_policy(1, partial(km2_fn, "domain.1"), "", "read")),
            sorted(
                [
                    ["admin", "domain.*", "data1", "read"],
                    ["user", "domain.1", "data2", "read"],
                    ["user", "domain.*", "data3", "read"],
                ]
            ),
        )

    def test_get_policy_multiple_matching_functions(self):
        e = self.get_enforcer(
            get_examples("rbac_with_domain_and_policy_pattern_model.conf"),
            get_examples("rbac_with_domain_and_policy_pattern_policy.csv"),
        )

        self.assertEqual(
            e.get_policy(),
            [
                ["admin", "domain.*", "data1", "read"],
                ["user", "domain.*", "data3", "read"],
                ["user", "domain.1", "data2", "read"],
                ["user", "domain.1", "data2", "write"],
            ],
        )

        km2_fn = casbin.util.key_match2_func

        self.assertEqual(
            sorted(
                e.get_filtered_policy(
                    1, partial(km2_fn, "domain.2"), lambda a: "data" in a
                )
            ),
            sorted(
                [
                    ["admin", "domain.*", "data1", "read"],
                    ["user", "domain.*", "data3", "read"],
                ]
            ),
        )

        self.assertEqual(
            sorted(
                e.get_filtered_policy(
                    1, partial(km2_fn, "domain.1"), lambda a: "data" in a, "read"
                )
            ),
            sorted(
                [
                    ["admin", "domain.*", "data1", "read"],
                    ["user", "domain.1", "data2", "read"],
                    ["user", "domain.*", "data3", "read"],
                ]
            ),
        )

        self.assertEqual(
            sorted(
                e.get_filtered_policy(
                    1, partial(km2_fn, "domain.1"), "", "reading".startswith
                )
            ),
            sorted(
                [
                    ["admin", "domain.*", "data1", "read"],
                    ["user", "domain.1", "data2", "read"],
                    ["user", "domain.*", "data3", "read"],
                ]
            ),
        )

    def test_modify_policy_api(self):
        e = self.get_enforcer(
            get_examples("rbac_model.conf"),
            get_examples("rbac_policy.csv"),
            # True,
        )
        self.assertEqual(
            e.get_policy(),
            [
                ["alice", "data1", "read"],
                ["bob", "data2", "write"],
                ["data2_admin", "data2", "read"],
                ["data2_admin", "data2", "write"],
            ],
        )

        e.add_policy("eve", "data3", "read")
        e.add_named_policy("p", ["eve", "data3", "write"])
        self.assertEqual(
            e.get_policy(),
            [
                ["alice", "data1", "read"],
                ["bob", "data2", "write"],
                ["data2_admin", "data2", "read"],
                ["data2_admin", "data2", "write"],
                ["eve", "data3", "read"],
                ["eve", "data3", "write"],
            ],
        )

        rules = [
            ["jack", "data4", "read"],
            ["katy", "data4", "write"],
            ["leyo", "data4", "read"],
            ["ham", "data4", "write"],
        ]

        named_policies = [
            ["jack", "data4", "write"],
            ["katy", "data4", "read"],
            ["leyo", "data4", "write"],
            ["ham", "data4", "read"],
        ]
        e.add_policies(rules)
        e.add_named_policies("p", named_policies)

        self.assertEqual(
            e.get_policy(),
            [
                ["alice", "data1", "read"],
                ["bob", "data2", "write"],
                ["data2_admin", "data2", "read"],
                ["data2_admin", "data2", "write"],
                ["eve", "data3", "read"],
                ["eve", "data3", "write"],
                ["jack", "data4", "read"],
                ["katy", "data4", "write"],
                ["leyo", "data4", "read"],
                ["ham", "data4", "write"],
                ["jack", "data4", "write"],
                ["katy", "data4", "read"],
                ["leyo", "data4", "write"],
                ["ham", "data4", "read"],
            ],
        )

        e.remove_policies(rules)
        e.remove_named_policies("p", named_policies)

        e.add_named_policy("p", "testing")
        self.assertEqual(
            e.get_policy(),
            [
                ["alice", "data1", "read"],
                ["bob", "data2", "write"],
                ["data2_admin", "data2", "read"],
                ["data2_admin", "data2", "write"],
                ["eve", "data3", "read"],
                ["eve", "data3", "write"],
                ["testing"],
            ],
        )


class TestManagementApiSynced(TestManagementApi):
    def get_enforcer(self, model=None, adapter=None):
        return casbin.SyncedEnforcer(
            model,
            adapter,
        )
