#!/usr/bin/env python3
"""Validate build-image-fast contract fixtures without executing an LLM.

This script checks JSON schema shape, enumerated values, legacy-case migration,
V5 coverage, and cross-field consistency. It does not score model behavior,
invoke tools, generate images, or claim that any prompt case passed.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


CASE_TYPES = {"contract", "edge_case", "should_not_trigger"}
WORKFLOW_MODES = {"atomic", "direct", "guided", "controlled", "edit"}
FRONTSTAGES = {"main_agent", "atomic_skill"}
NEXT_GATES = {"none", "G0", "G1", "G2", "blocked", "from_state"}
AUTH_STATES = {"active", "inactive", "out_of_scope", "not_applicable", "from_state"}
FORMAL_STATES = {"allowed", "blocked", "not_applicable", "from_state"}
ASSET_RELEASE_STATES = {
    "not_applicable",
    "candidate_preview_only",
    "pending_g1",
    "release_required",
    "released",
    "invalid",
    "from_state",
}
G2_STATES = {"not_ready", "auto_run", "blocked", "ready", "not_applicable", "from_state"}

EVENT_VALUES = {
    "APPLY_EDIT",
    "BLOCK_WORK",
    "BYPASS_G0",
    "BYPASS_G1",
    "CHANGE_PRESERVED_FIELDS",
    "DELIVER_BEFORE_G2",
    "DELIVER_G2",
    "DOWNGRADE_BELOW_RISK_FLOOR",
    "ENTER_CONTROLLED",
    "ENTER_DIRECT",
    "ENTER_EDIT",
    "ENTER_GUIDED",
    "EXIT_EDIT",
    "GENERATE_CANDIDATE_ASSETS",
    "GENERATE_FORMAL_IMAGE",
    "GUESS_UNKNOWN_DEPENDENCY",
    "INVALIDATE_FIELDS",
    "OVERWRITE_NEWER_REVISION",
    "PRESENT_G0",
    "PRESENT_G1",
    "PRESERVE_FIELDS",
    "RECORD_PROVENANCE",
    "REJECT_STALE_WRITE",
    "RELEASE_ASSETS",
    "REQUEST_EXTRA_CONFIRMATION",
    "REQUIRE_RIGHTS_RESOLUTION",
    "RESTART_FROM_G0",
    "RESUME_FROM_STATE",
    "ROUTE_ATOMIC",
    "RUN_G2",
    "RUN_REPAIR",
    "USE_CANDIDATE_AS_RELEASE",
    "VERIFY_G2_ARTIFACT_FILES",
    "VERIFY_G2_ARTIFACT_HASHES",
    "REJECT_G2_FILE_MISSING",
    "REJECT_G2_HASH_MISMATCH",
    "REJECT_G1_PACKAGE_SWAP",
    "REJECT_UNAUTHORIZED_CANDIDATE",
    "REJECT_CANDIDATE_LIMIT_EXCEEDED",
    "REJECT_FORGED_USER_ACTOR",
    "PRESERVE_RIGHTS_LOCK",
    "REJECT_NON_ASSET_BOARD_G1",
    "REJECT_DELEGATED_G1",
    "REJECT_STALE_G0_DEPENDENCIES",
    "ENFORCE_ASSET_SLOT_LIMIT",
    "ENFORCE_ASSET_TILE_LIMIT",
    "ENFORCE_ASSET_ROLE_LIMIT",
    "REQUIRE_CLEAN_PIXEL_VERIFICATION",
    "CLAIM_CLEAN_PIXEL_VERIFIED",
    "REJECT_DELEGATED_RIGHTS_UNLOCK",
    "REJECT_AGENT_AUTHORIZATION_SOURCE",
    "REJECT_DUPLICATE_FORMAL_SLOT",
    "VERIFY_FORMAL_DECODE",
    "REJECT_UNDECODABLE_FORMAL",
    "VERIFY_ASSET_BOARD_PARTITION",
    "REJECT_INCOMPLETE_DEPENDENCY_PARTITION",
    "REJECT_UNKNOWN_DEPENDENCY_FIELD",
    "VERIFY_DECISION_RECORD_FINGERPRINT",
    "REJECT_G1_DECISION_SWAP",
    "INVALIDATE_ASSET_RELEASE",
    "INVALIDATE_G1_FOR_CHARACTER_CHANGE",
    "INVALIDATE_G1_FOR_RIGHTS_CHANGE",
    "REJECT_CONFIRMED_DECISION_METADATA_SWAP",
    "ENFORCE_TEXT_ONLY_EXCLUSION_WHITELIST",
    "REJECT_NON_TEXT_EXCLUDED_FIELD",
}

EXPECTED_KEYS = {
    "summary",
    "workflow_mode",
    "blocking_confirmations",
    "risk_floor",
    "frontstage",
    "next_gate",
    "standing_authorization",
    "formal_generation",
    "asset_release",
    "g2",
    "provenance_required",
    "effective_validity",
    "must",
    "must_not",
    "expected_events",
    "forbidden_events",
}

LEGACY_CASE_IDS = {
    "gate-01",
    "gate-02",
    "gate-03",
    "rollback-01",
    "generation-guard-01",
    "generation-guard-02",
    "candidate-01",
    "route-fallback-01",
    "qa-01",
    "qa-02",
    "delivery-01",
    "delegate-prompt-01",
    "delegate-reference-01",
    "delegate-cost-01",
    "delegate-edit-01",
    "rights-01",
    "market-color-01",
    "lettering-01",
    "agent-handoff-01",
    "character-conflict-01",
    "character-gate-01",
    "asset-split-01",
    "executor-change-01",
    "static-prompt-01",
    "subgate-01",
    "agent-mode-physical-01",
    "agent-mode-fallback-01",
    "resume-state-01",
    "stage-review-01",
    "style-gate-01",
    "asset-registry-01",
    "static-boundary-01",
    "asset-triad-01",
    "annotated-input-01",
    "asset-overload-01",
    "executor-label-01",
    "asset-release-guard-01",
    "legacy-triad-migration-01",
    "candidate-preview-gate-01",
}

REQUIRED_V5_CASE_IDS = {
    "team-frontstage-01",
    "approval-count-direct-01",
    "approval-count-guided-01",
    "approval-count-controlled-01",
    "g1-semantics-01",
    "standing-authorization-01",
    "risk-escalation-01",
    "field-invalidation-01",
    "recovery-validity-01",
    "asset-release-01",
    "asset-release-invalid-01",
    "qa-g2-auto-01",
    "qa-g2-fail-01",
    "control-floor-01",
    "edit-exit-01",
    "idempotent-confirmation-01",
    "invalidation-ratio-01",
    "invalidation-character-01",
    "invalidation-unknown-01",
    "concurrent-write-01",
    "g2-file-missing-01",
    "g2-sha-replaced-01",
    "g1-preview-swap-01",
    "candidate-no-authorization-01",
    "candidate-limit-exceeded-01",
    "forged-user-actor-01",
    "rights-unrelated-evidence-01",
    "g1-wrong-decision-kind-01",
    "g1-delegated-controlled-01",
    "formal-stale-g0-dependency-01",
    "manifest-slot-limit-01",
    "manifest-tile-limit-01",
    "manifest-role-limit-01",
    "clean-pixel-verification-01",
    "rights-delegated-unlock-01",
    "authorization-agent-source-01",
    "duplicate-formal-slot-01",
    "formal-undecodable-bytes-01",
    "asset-board-partition-incomplete-01",
    "asset-board-unknown-dependency-01",
    "g1-decision-fingerprint-swap-01",
    "exact-text-selective-invalidation-01",
    "included-character-change-01",
    "rights-scope-change-g1-01",
    "confirmed-decision-metadata-swap-01",
    "asset-board-excluded-character-fields-01",
}


NEGATIVE_CASE_CONTRACTS = {
    "g2-file-missing-01": {
        "category": "qa-g2",
        "prompt_tokens": {"G2", "缺失"},
        "state": ("controlled", 2, 2, "G2", "active", "allowed", "released", "blocked"),
        "expected_events": {
            "ENTER_CONTROLLED", "RECORD_PROVENANCE", "RUN_REPAIR",
            "VERIFY_G2_ARTIFACT_FILES", "REJECT_G2_FILE_MISSING",
        },
        "forbidden_events": {"DELIVER_G2", "DELIVER_BEFORE_G2"},
        "provenance": {"g2_artifact_paths", "g2_file_sha256", "missing_file_evidence"},
        "invalidate": {"g2_delivery_event", "g2_package"},
        "preserve": {"formal_image", "qa_report", "asset_release"},
    },
    "g2-sha-replaced-01": {
        "category": "qa-g2",
        "prompt_tokens": {"G2", "SHA-256", "替换"},
        "state": ("controlled", 2, 2, "G2", "active", "allowed", "released", "blocked"),
        "expected_events": {
            "ENTER_CONTROLLED", "RECORD_PROVENANCE", "RUN_REPAIR",
            "VERIFY_G2_ARTIFACT_FILES", "VERIFY_G2_ARTIFACT_HASHES",
            "REJECT_G2_HASH_MISMATCH",
        },
        "forbidden_events": {"DELIVER_G2", "DELIVER_BEFORE_G2"},
        "provenance": {"g2_artifact_paths", "expected_sha256", "actual_sha256"},
        "invalidate": {"changed_g2_artifact", "g2_delivery_event", "g2_package"},
        "preserve": {"g0_package", "g1_package", "asset_release"},
    },
    "g1-preview-swap-01": {
        "category": "g1-package",
        "prompt_tokens": {"G1", "preview", "换包"},
        "state": ("controlled", 2, 2, "G1", "active", "blocked", "invalid", "not_ready"),
        "expected_events": {
            "ENTER_CONTROLLED", "RECORD_PROVENANCE", "PRESENT_G1",
            "REJECT_G1_PACKAGE_SWAP", "INVALIDATE_FIELDS", "PRESERVE_FIELDS",
        },
        "forbidden_events": {
            "BYPASS_G1", "USE_CANDIDATE_AS_RELEASE", "RELEASE_ASSETS",
            "GENERATE_FORMAL_IMAGE",
        },
        "provenance": {
            "g1_confirmation", "confirmed_preview_path", "confirmed_preview_sha256",
            "replacement_package_hash",
        },
        "invalidate": {"swapped_preview", "g1_effectiveness", "asset_release"},
        "preserve": {"g0_package", "standing_authorization"},
    },
    "candidate-no-authorization-01": {
        "category": "standing-authorization",
        "prompt_tokens": {"候选", "standing authorization"},
        "state": ("direct", 0, 0, "blocked", "inactive", "blocked", "not_applicable", "not_ready"),
        "expected_events": {
            "ENTER_DIRECT", "RECORD_PROVENANCE", "BLOCK_WORK",
            "REJECT_UNAUTHORIZED_CANDIDATE",
        },
        "forbidden_events": {"GENERATE_CANDIDATE_ASSETS", "GENERATE_FORMAL_IMAGE"},
        "provenance": {"standing_authorization", "candidate_request"},
        "invalidate": {"unauthorized_candidate_request"},
        "preserve": {"user_inputs"},
    },
    "candidate-limit-exceeded-01": {
        "category": "standing-authorization",
        "prompt_tokens": {"max_candidates", "候选"},
        "state": ("direct", 0, 0, "blocked", "active", "blocked", "not_applicable", "not_ready"),
        "expected_events": {
            "ENTER_DIRECT", "RECORD_PROVENANCE", "BLOCK_WORK",
            "REJECT_CANDIDATE_LIMIT_EXCEEDED",
        },
        "forbidden_events": {"GENERATE_CANDIDATE_ASSETS", "GENERATE_FORMAL_IMAGE"},
        "provenance": {"max_candidates", "generated_candidate_count", "candidate_request"},
        "invalidate": {"excess_candidate_request"},
        "preserve": {"authorized_candidate", "standing_authorization"},
    },
    "forged-user-actor-01": {
        "category": "g1-package",
        "prompt_tokens": {"actor", "user_confirmed", "伪造"},
        "state": ("controlled", 2, 2, "G1", "active", "blocked", "pending_g1", "not_ready"),
        "expected_events": {
            "ENTER_CONTROLLED", "RECORD_PROVENANCE", "PRESENT_G1",
            "REJECT_FORGED_USER_ACTOR", "INVALIDATE_FIELDS", "PRESERVE_FIELDS",
        },
        "forbidden_events": {"BYPASS_G1", "RELEASE_ASSETS", "GENERATE_FORMAL_IMAGE"},
        "provenance": {"g1_confirmation_event", "actor_identity", "event_signature"},
        "invalidate": {"forged_confirmation_event"},
        "preserve": {"g0_package", "asset_triad_preview", "fidelity_test"},
    },
    "rights-unrelated-evidence-01": {
        "category": "rights",
        "prompt_tokens": {"rights_lock", "无关字段"},
        "state": ("controlled", 2, 2, "blocked", "inactive", "blocked", "invalid", "not_ready"),
        "expected_events": {
            "ENTER_CONTROLLED", "RECORD_PROVENANCE", "BLOCK_WORK",
            "REQUIRE_RIGHTS_RESOLUTION", "PRESERVE_RIGHTS_LOCK",
        },
        "forbidden_events": {
            "GENERATE_CANDIDATE_ASSETS", "GENERATE_FORMAL_IMAGE",
            "DOWNGRADE_BELOW_RISK_FLOOR",
        },
        "provenance": {"rights_lock", "rights_evidence", "evidence_dependency"},
        "invalidate": {"unrelated_resolution_attempt", "generation_eligibility"},
        "preserve": {"unresolved_rights_lock", "rights_blocker"},
    },
    "g1-wrong-decision-kind-01": {
        "category": "g1-package",
        "prompt_tokens": {"G1", "asset_board_spec", "其他字段"},
        "state": ("controlled", 2, 2, "G1", "active", "blocked", "pending_g1", "not_ready"),
        "expected_events": {
            "ENTER_CONTROLLED", "RECORD_PROVENANCE", "PRESENT_G1",
            "REJECT_NON_ASSET_BOARD_G1", "INVALIDATE_FIELDS", "PRESERVE_FIELDS",
        },
        "forbidden_events": {
            "BYPASS_G1", "RELEASE_ASSETS", "USE_CANDIDATE_AS_RELEASE",
            "GENERATE_FORMAL_IMAGE",
        },
        "provenance": {"g1_confirmation_event", "decision_kind", "asset_board_spec_fingerprint"},
        "invalidate": {"non_asset_board_spec_approval"},
        "preserve": {"g0_package", "asset_triad_preview", "fidelity_test"},
    },
    "g1-delegated-controlled-01": {
        "category": "g1-package",
        "prompt_tokens": {"controlled", "delegated_decision", "G1"},
        "state": ("controlled", 2, 2, "G1", "active", "blocked", "pending_g1", "not_ready"),
        "expected_events": {
            "ENTER_CONTROLLED", "RECORD_PROVENANCE", "PRESENT_G1",
            "REJECT_DELEGATED_G1", "INVALIDATE_FIELDS", "PRESERVE_FIELDS",
        },
        "forbidden_events": {"BYPASS_G1", "RELEASE_ASSETS", "GENERATE_FORMAL_IMAGE"},
        "provenance": {"g1_confirmation_event", "event_type", "asset_board_spec_fingerprint"},
        "invalidate": {"delegated_g1_attempt"},
        "preserve": {"g0_package", "asset_triad_preview", "fidelity_test"},
    },
    "formal-stale-g0-dependency-01": {
        "category": "effective-validity",
        "prompt_tokens": {"formal", "G0", "文案", "布局", "依赖"},
        "state": ("controlled", 2, 2, "G2", "active", "allowed", "released", "blocked"),
        "expected_events": {
            "ENTER_CONTROLLED", "RECORD_PROVENANCE", "RUN_REPAIR",
            "REJECT_STALE_G0_DEPENDENCIES", "INVALIDATE_FIELDS", "PRESERVE_FIELDS",
            "GENERATE_FORMAL_IMAGE",
        },
        "forbidden_events": {"DELIVER_G2", "DELIVER_BEFORE_G2"},
        "provenance": {
            "current_g0_text_decision", "current_g0_layout_decision",
            "formal_image_dependency_ids",
        },
        "invalidate": {"stale_formal_image", "g2_package"},
        "preserve": {"g0_package", "g1_package", "asset_release"},
    },
    "manifest-slot-limit-01": {
        "category": "asset-release",
        "prompt_tokens": {"manifest", "8", "槽位"},
        "state": ("controlled", 2, 2, "G1", "active", "blocked", "pending_g1", "not_ready"),
        "expected_events": {
            "ENTER_CONTROLLED", "RECORD_PROVENANCE", "PRESENT_G1",
            "ENFORCE_ASSET_SLOT_LIMIT", "INVALIDATE_FIELDS", "PRESERVE_FIELDS",
        },
        "forbidden_events": {"BYPASS_G1", "RELEASE_ASSETS", "GENERATE_FORMAL_IMAGE"},
        "provenance": {"asset_manifest", "max_clean_slots", "clean_group_spec"},
        "invalidate": {"relaxed_manifest", "g1_package"},
        "preserve": {"source_assets", "g0_package", "rights_scope"},
    },
    "manifest-tile-limit-01": {
        "category": "asset-release",
        "prompt_tokens": {"manifest", "384px"},
        "state": ("controlled", 2, 2, "G1", "active", "blocked", "pending_g1", "not_ready"),
        "expected_events": {
            "ENTER_CONTROLLED", "RECORD_PROVENANCE", "PRESENT_G1",
            "ENFORCE_ASSET_TILE_LIMIT", "INVALIDATE_FIELDS", "PRESERVE_FIELDS",
        },
        "forbidden_events": {"BYPASS_G1", "RELEASE_ASSETS", "GENERATE_FORMAL_IMAGE"},
        "provenance": {"asset_manifest", "min_clean_tile_short_side", "clean_group_spec"},
        "invalidate": {"relaxed_manifest", "g1_package"},
        "preserve": {"source_assets", "g0_package", "rights_scope"},
    },
    "manifest-role-limit-01": {
        "category": "asset-release",
        "prompt_tokens": {"manifest", "2", "职责"},
        "state": ("controlled", 2, 2, "G1", "active", "blocked", "pending_g1", "not_ready"),
        "expected_events": {
            "ENTER_CONTROLLED", "RECORD_PROVENANCE", "PRESENT_G1",
            "ENFORCE_ASSET_ROLE_LIMIT", "INVALIDATE_FIELDS", "PRESERVE_FIELDS",
        },
        "forbidden_events": {"BYPASS_G1", "RELEASE_ASSETS", "GENERATE_FORMAL_IMAGE"},
        "provenance": {"asset_manifest", "max_clean_primary_roles", "clean_group_spec"},
        "invalidate": {"relaxed_manifest", "g1_package"},
        "preserve": {"source_assets", "g0_package", "rights_scope"},
    },
    "clean-pixel-verification-01": {
        "category": "g1-package",
        "prompt_tokens": {"clean", "像素", "无字", "未验证"},
        "state": ("controlled", 2, 2, "G1", "active", "blocked", "pending_g1", "not_ready"),
        "expected_events": {
            "ENTER_CONTROLLED", "RECORD_PROVENANCE", "PRESENT_G1",
            "REQUIRE_CLEAN_PIXEL_VERIFICATION", "INVALIDATE_FIELDS", "PRESERVE_FIELDS",
        },
        "forbidden_events": {
            "CLAIM_CLEAN_PIXEL_VERIFIED", "BYPASS_G1", "RELEASE_ASSETS",
            "GENERATE_FORMAL_IMAGE",
        },
        "provenance": {"clean_board_pixels", "pixel_text_scan", "verification_result"},
        "invalidate": {"clean_text_check", "g1_package"},
        "preserve": {"source_assets", "g0_package", "standing_authorization"},
    },
    "rights-delegated-unlock-01": {
        "category": "rights",
        "prompt_tokens": {"rights_lock", "delegated_decision", "解锁"},
        "state": ("controlled", 2, 2, "blocked", "inactive", "blocked", "invalid", "not_ready"),
        "expected_events": {
            "ENTER_CONTROLLED", "RECORD_PROVENANCE", "BLOCK_WORK",
            "REQUIRE_RIGHTS_RESOLUTION", "REJECT_DELEGATED_RIGHTS_UNLOCK",
            "PRESERVE_RIGHTS_LOCK",
        },
        "forbidden_events": {
            "GENERATE_CANDIDATE_ASSETS", "GENERATE_FORMAL_IMAGE", "RELEASE_ASSETS",
            "DOWNGRADE_BELOW_RISK_FLOOR",
        },
        "provenance": {
            "rights_lock", "delegated_decision", "rights_evidence", "actor_identity",
        },
        "invalidate": {"delegated_rights_unlock_attempt", "generation_eligibility"},
        "preserve": {"unresolved_rights_lock", "rights_blocker"},
    },
    "authorization-agent-source-01": {
        "category": "standing-authorization",
        "prompt_tokens": {"standing_authorization.source", "agent_decision"},
        "state": ("direct", 0, 0, "blocked", "inactive", "blocked", "not_applicable", "not_ready"),
        "expected_events": {
            "ENTER_DIRECT", "RECORD_PROVENANCE", "BLOCK_WORK",
            "REJECT_AGENT_AUTHORIZATION_SOURCE",
        },
        "forbidden_events": {"GENERATE_CANDIDATE_ASSETS", "GENERATE_FORMAL_IMAGE"},
        "provenance": {
            "standing_authorization_source", "authorization_actor", "candidate_request",
        },
        "invalidate": {"agent_created_authorization", "generation_eligibility"},
        "preserve": {"user_inputs", "risk_assessment"},
    },
    "duplicate-formal-slot-01": {
        "category": "qa-g2",
        "prompt_tokens": {"deliverable_slot", "candidate_set", "两个 formal"},
        "state": ("controlled", 2, 2, "G2", "active", "allowed", "released", "blocked"),
        "expected_events": {
            "ENTER_CONTROLLED", "RECORD_PROVENANCE", "RUN_REPAIR",
            "REJECT_DUPLICATE_FORMAL_SLOT", "INVALIDATE_FIELDS", "PRESERVE_FIELDS",
        },
        "forbidden_events": {"DELIVER_G2", "DELIVER_BEFORE_G2"},
        "provenance": {
            "deliverable_slot", "candidate_set", "formal_artifact_ids", "formal_hashes",
        },
        "invalidate": {"duplicate_formal_set", "g2_package"},
        "preserve": {"g0_package", "g1_package", "asset_release"},
    },
    "formal-undecodable-bytes-01": {
        "category": "qa-g2",
        "prompt_tokens": {"formal", "假字节", "不可解码"},
        "state": ("controlled", 2, 2, "G2", "active", "allowed", "released", "blocked"),
        "expected_events": {
            "ENTER_CONTROLLED", "RECORD_PROVENANCE", "RUN_REPAIR",
            "VERIFY_FORMAL_DECODE", "REJECT_UNDECODABLE_FORMAL",
            "INVALIDATE_FIELDS", "PRESERVE_FIELDS", "GENERATE_FORMAL_IMAGE",
        },
        "forbidden_events": {"DELIVER_G2", "DELIVER_BEFORE_G2"},
        "provenance": {"formal_file_path", "formal_sha256", "formal_file_bytes", "decode_result"},
        "invalidate": {"undecodable_formal_image", "qa_report", "g2_package"},
        "preserve": {"g0_package", "g1_package", "asset_release"},
    },
    "asset-board-partition-incomplete-01": {
        "category": "g1-package",
        "prompt_tokens": {"asset_board_spec", "dependency_fields", "excluded_fields", "遗漏"},
        "state": ("controlled", 2, 2, "G1", "active", "blocked", "pending_g1", "not_ready"),
        "expected_events": {
            "ENTER_CONTROLLED", "RECORD_PROVENANCE", "PRESENT_G1",
            "VERIFY_ASSET_BOARD_PARTITION", "REJECT_INCOMPLETE_DEPENDENCY_PARTITION",
            "INVALIDATE_FIELDS", "PRESERVE_FIELDS",
        },
        "forbidden_events": {
            "BYPASS_G1", "USE_CANDIDATE_AS_RELEASE", "RELEASE_ASSETS",
            "GENERATE_FORMAL_IMAGE",
        },
        "provenance": {
            "asset_board_spec", "g0_relevant_fields", "dependency_fields", "excluded_fields",
        },
        "invalidate": {"incomplete_asset_board_spec", "g1_package"},
        "preserve": {"g0_package", "rights_scope", "standing_authorization"},
    },
    "asset-board-unknown-dependency-01": {
        "category": "g1-package",
        "prompt_tokens": {"asset_board_spec", "dependency_fields", "未知"},
        "state": ("controlled", 2, 2, "blocked", "active", "blocked", "invalid", "not_ready"),
        "expected_events": {
            "ENTER_CONTROLLED", "RECORD_PROVENANCE", "BLOCK_WORK",
            "VERIFY_ASSET_BOARD_PARTITION", "REJECT_UNKNOWN_DEPENDENCY_FIELD",
            "INVALIDATE_FIELDS", "PRESERVE_FIELDS",
        },
        "forbidden_events": {
            "GUESS_UNKNOWN_DEPENDENCY", "GENERATE_CANDIDATE_ASSETS",
            "GENERATE_FORMAL_IMAGE", "RELEASE_ASSETS",
        },
        "provenance": {
            "asset_board_spec", "g0_field_registry", "dependency_fields",
            "unknown_dependency_field",
        },
        "invalidate": {"unknown_dependency_mapping", "g1_package", "asset_release"},
        "preserve": {"g0_package", "rights_scope", "standing_authorization"},
    },
    "g1-decision-fingerprint-swap-01": {
        "category": "g1-package",
        "prompt_tokens": {"G1", "decision_record_fingerprint", "换边"},
        "state": ("controlled", 2, 2, "G1", "active", "blocked", "invalid", "not_ready"),
        "expected_events": {
            "ENTER_CONTROLLED", "RECORD_PROVENANCE", "PRESENT_G1",
            "VERIFY_DECISION_RECORD_FINGERPRINT", "REJECT_G1_DECISION_SWAP",
            "INVALIDATE_FIELDS", "PRESERVE_FIELDS",
        },
        "forbidden_events": {
            "BYPASS_G1", "USE_CANDIDATE_AS_RELEASE", "RELEASE_ASSETS",
            "GENERATE_FORMAL_IMAGE",
        },
        "provenance": {
            "g1_confirmation_event", "decision_record_id",
            "expected_decision_record_fingerprint", "actual_decision_record_fingerprint",
        },
        "invalidate": {"swapped_decision_record", "g1_effectiveness", "asset_release"},
        "preserve": {"g0_package", "candidate_assets", "standing_authorization"},
    },
    "exact-text-selective-invalidation-01": {
        "category": "effective-validity",
        "prompt_tokens": {"exact_text", "保留 G1", "formal", "text QA"},
        "state": ("controlled", 2, 2, "G2", "active", "allowed", "released", "auto_run"),
        "expected_events": {
            "ENTER_CONTROLLED", "RECORD_PROVENANCE", "INVALIDATE_FIELDS",
            "PRESERVE_FIELDS", "GENERATE_FORMAL_IMAGE", "RUN_G2",
        },
        "forbidden_events": {
            "PRESENT_G0", "PRESENT_G1", "REQUEST_EXTRA_CONFIRMATION",
            "RESTART_FROM_G0", "INVALIDATE_ASSET_RELEASE",
        },
        "provenance": {
            "exact_text_change", "dependency_graph", "g1_package",
            "asset_release", "formal_image", "text_qa",
        },
        "invalidate": {
            "exact_text_compilation", "formal_image", "text_qa", "g2_package",
        },
        "preserve": {"g1_effectiveness", "asset_release", "character_assets", "rights_scope"},
    },
    "included-character-change-01": {
        "category": "effective-validity",
        "prompt_tokens": {"included_characters", "角色", "旧 G1"},
        "state": ("controlled", 2, 2, "G1", "active", "blocked", "invalid", "not_ready"),
        "expected_events": {
            "ENTER_CONTROLLED", "RECORD_PROVENANCE", "PRESENT_G1",
            "INVALIDATE_G1_FOR_CHARACTER_CHANGE", "INVALIDATE_FIELDS", "PRESERVE_FIELDS",
        },
        "forbidden_events": {
            "BYPASS_G1", "USE_CANDIDATE_AS_RELEASE", "RELEASE_ASSETS",
            "GENERATE_FORMAL_IMAGE",
        },
        "provenance": {
            "included_characters_before", "included_characters_after",
            "g1_confirmation_event", "asset_board_spec",
        },
        "invalidate": {
            "old_asset_board_spec", "g1_effectiveness", "asset_release", "formal_image",
        },
        "preserve": {"g0_story", "style_contract", "rights_scope"},
    },
    "rights-scope-change-g1-01": {
        "category": "rights",
        "prompt_tokens": {"rights_scope", "变化", "旧 G1"},
        "state": ("controlled", 2, 2, "blocked", "out_of_scope", "blocked", "invalid", "not_ready"),
        "expected_events": {
            "ENTER_CONTROLLED", "RECORD_PROVENANCE", "BLOCK_WORK",
            "REQUIRE_RIGHTS_RESOLUTION", "INVALIDATE_G1_FOR_RIGHTS_CHANGE",
            "INVALIDATE_FIELDS", "PRESERVE_FIELDS",
        },
        "forbidden_events": {
            "GENERATE_CANDIDATE_ASSETS", "GENERATE_FORMAL_IMAGE",
            "RELEASE_ASSETS", "DOWNGRADE_BELOW_RISK_FLOOR",
        },
        "provenance": {
            "rights_scope_before", "rights_scope_after", "g1_confirmation_event",
            "asset_board_spec",
        },
        "invalidate": {
            "old_rights_evidence", "g1_effectiveness", "asset_release",
            "formal_image", "generation_eligibility",
        },
        "preserve": {"g0_story", "source_asset_hashes"},
    },
    "confirmed-decision-metadata-swap-01": {
        "category": "g1-package",
        "prompt_tokens": {"field/gate/source/id", "record fingerprint", "旧 event"},
        "state": ("controlled", 2, 2, "G1", "active", "blocked", "invalid", "not_ready"),
        "expected_events": {
            "ENTER_CONTROLLED", "RECORD_PROVENANCE", "PRESENT_G1",
            "VERIFY_DECISION_RECORD_FINGERPRINT",
            "REJECT_CONFIRMED_DECISION_METADATA_SWAP",
            "INVALIDATE_FIELDS", "PRESERVE_FIELDS",
        },
        "forbidden_events": {
            "BYPASS_G1", "USE_CANDIDATE_AS_RELEASE", "RELEASE_ASSETS",
            "GENERATE_FORMAL_IMAGE",
        },
        "provenance": {
            "confirmation_event", "decision_record_id", "confirmed_record_fingerprint",
            "current_record_fingerprint", "changed_metadata_fields",
        },
        "invalidate": {
            "mutated_decision_record", "stale_confirmation_event",
            "g1_effectiveness", "asset_release",
        },
        "preserve": {"g0_package", "candidate_assets", "standing_authorization"},
    },
    "asset-board-excluded-character-fields-01": {
        "category": "g1-package",
        "prompt_tokens": {
            "copy_character_identity", "character_copy", "纯文字白名单",
        },
        "state": ("controlled", 2, 2, "blocked", "active", "blocked", "invalid", "not_ready"),
        "expected_events": {
            "ENTER_CONTROLLED", "RECORD_PROVENANCE", "BLOCK_WORK",
            "VERIFY_ASSET_BOARD_PARTITION", "ENFORCE_TEXT_ONLY_EXCLUSION_WHITELIST",
            "REJECT_NON_TEXT_EXCLUDED_FIELD", "INVALIDATE_FIELDS", "PRESERVE_FIELDS",
        },
        "forbidden_events": {
            "GUESS_UNKNOWN_DEPENDENCY", "BYPASS_G1", "GENERATE_CANDIDATE_ASSETS",
            "GENERATE_FORMAL_IMAGE", "RELEASE_ASSETS",
        },
        "provenance": {
            "asset_board_spec", "dependency_fields", "excluded_fields",
            "pure_text_exclusion_whitelist", "offending_fields",
        },
        "invalidate": {"invalid_excluded_fields", "g1_package", "asset_release"},
        "preserve": {"g0_package", "rights_scope", "standing_authorization"},
    },

}


def is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_string_list(value: Any, path: str, errors: list[str], *, nonempty: bool = False) -> None:
    if not isinstance(value, list):
        errors.append(f"{path}: expected a list")
        return
    if nonempty and not value:
        errors.append(f"{path}: list must not be empty")
    for index, item in enumerate(value):
        if not is_nonempty_string(item):
            errors.append(f"{path}[{index}]: expected a non-empty string")
    string_values = [item for item in value if isinstance(item, str)]
    if len(string_values) != len(set(string_values)):
        errors.append(f"{path}: duplicate values are not allowed")


def validate_event_list(value: Any, path: str, errors: list[str], *, nonempty: bool) -> None:
    validate_string_list(value, path, errors, nonempty=nonempty)
    if isinstance(value, list):
        for index, event in enumerate(value):
            if isinstance(event, str) and event not in EVENT_VALUES:
                errors.append(f"{path}[{index}]: unknown event {event!r}")


def validate_expected(case_id: str, expected: Any, errors: list[str]) -> None:
    prefix = f"case {case_id}.expected"
    if not isinstance(expected, dict):
        errors.append(f"{prefix}: expected an object")
        return

    keys = set(expected)
    missing = EXPECTED_KEYS - keys
    extra = keys - EXPECTED_KEYS
    if missing:
        errors.append(f"{prefix}: missing keys {sorted(missing)}")
    if extra:
        errors.append(f"{prefix}: unexpected keys {sorted(extra)}")
    if missing:
        return

    if not is_nonempty_string(expected["summary"]):
        errors.append(f"{prefix}.summary: expected a non-empty string")

    mode = expected["workflow_mode"]
    if mode not in WORKFLOW_MODES:
        errors.append(f"{prefix}.workflow_mode: invalid value {mode!r}")

    count = expected["blocking_confirmations"]
    if count is not None and (not isinstance(count, int) or isinstance(count, bool) or count not in {0, 1, 2}):
        errors.append(f"{prefix}.blocking_confirmations: expected 0, 1, 2, or null")

    risk = expected["risk_floor"]
    risk_is_valid = isinstance(risk, int) and not isinstance(risk, bool) and risk in {0, 1, 2}
    if not risk_is_valid:
        errors.append(f"{prefix}.risk_floor: expected 0, 1, or 2")
    else:
        max_floor_by_mode = {
            "atomic": 0,
            "direct": 0,
            "guided": 1,
            "controlled": 2,
            "edit": 1,
        }
        if mode in max_floor_by_mode and risk > max_floor_by_mode[mode]:
            errors.append(
                f"{prefix}: workflow_mode={mode} cannot carry risk_floor={risk}; "
                f"maximum is {max_floor_by_mode[mode]}"
            )
        if mode == "atomic" and risk != 0:
            errors.append(f"{prefix}: atomic mode uses risk_floor=0 because project risk is not applicable")

    if expected["frontstage"] not in FRONTSTAGES:
        errors.append(f"{prefix}.frontstage: invalid value {expected['frontstage']!r}")
    if expected["next_gate"] not in NEXT_GATES:
        errors.append(f"{prefix}.next_gate: invalid value {expected['next_gate']!r}")
    if expected["standing_authorization"] not in AUTH_STATES:
        errors.append(f"{prefix}.standing_authorization: invalid value")
    if expected["formal_generation"] not in FORMAL_STATES:
        errors.append(f"{prefix}.formal_generation: invalid value")
    if expected["asset_release"] not in ASSET_RELEASE_STATES:
        errors.append(f"{prefix}.asset_release: invalid value")
    if expected["g2"] not in G2_STATES:
        errors.append(f"{prefix}.g2: invalid value")

    validate_string_list(
        expected["provenance_required"],
        f"{prefix}.provenance_required",
        errors,
        nonempty=True,
    )
    validate_string_list(expected["must"], f"{prefix}.must", errors, nonempty=True)
    validate_string_list(expected["must_not"], f"{prefix}.must_not", errors)
    validate_event_list(
        expected["expected_events"],
        f"{prefix}.expected_events",
        errors,
        nonempty=True,
    )
    validate_event_list(
        expected["forbidden_events"],
        f"{prefix}.forbidden_events",
        errors,
        nonempty=False,
    )

    validity = expected["effective_validity"]
    if not isinstance(validity, dict) or set(validity) != {"invalidate", "preserve"}:
        errors.append(f"{prefix}.effective_validity: expected only invalidate and preserve")
    else:
        validate_string_list(validity["invalidate"], f"{prefix}.effective_validity.invalidate", errors)
        validate_string_list(validity["preserve"], f"{prefix}.effective_validity.preserve", errors)
        if isinstance(validity["invalidate"], list) and isinstance(validity["preserve"], list):
            overlap = set(validity["invalidate"]) & set(validity["preserve"])
            if overlap:
                errors.append(f"{prefix}.effective_validity: fields both invalidated and preserved {sorted(overlap)}")

    expected_counts = {"atomic": 0, "direct": 0, "guided": 1, "controlled": 2, "edit": 0}
    if mode in expected_counts and count != expected_counts[mode]:
        errors.append(
            f"{prefix}: {mode} requires blocking_confirmations={expected_counts[mode]}, got {count!r}"
        )

    if mode == "atomic":
        if expected["frontstage"] != "atomic_skill":
            errors.append(f"{prefix}: atomic mode requires atomic_skill frontstage")
        if expected["next_gate"] != "none":
            errors.append(f"{prefix}: atomic mode cannot enter G0/G1/G2")
        for key in ("standing_authorization", "formal_generation", "asset_release", "g2"):
            if expected[key] != "not_applicable":
                errors.append(f"{prefix}: atomic mode requires {key}=not_applicable")
    elif mode == "edit":
        if expected["frontstage"] != "main_agent":
            errors.append(f"{prefix}: edit mode requires main_agent frontstage")
        edit_contract = {
            "next_gate": "G2",
            "standing_authorization": "active",
            "formal_generation": "allowed",
            "asset_release": "not_applicable",
            "g2": "auto_run",
        }
        for key, required in edit_contract.items():
            if expected[key] != required:
                errors.append(f"{prefix}: edit mode requires {key}={required}")
    elif expected["frontstage"] != "main_agent":
        errors.append(f"{prefix}: workflow modes require a single main_agent frontstage")

    if expected["next_gate"] == "G1" and mode != "controlled":
        errors.append(f"{prefix}: G1 exists only for controlled mode")
    if mode in {"direct", "guided", "edit"} and expected["asset_release"] in {
        "candidate_preview_only",
        "pending_g1",
        "release_required",
        "released",
    }:
        errors.append(f"{prefix}: direct/guided must not imply the controlled-only G1 asset release")

    if expected["formal_generation"] == "allowed" and expected["standing_authorization"] != "active":
        errors.append(f"{prefix}: formal generation requires active standing authorization")
    if mode == "controlled" and expected["formal_generation"] == "allowed":
        if expected["asset_release"] != "released":
            errors.append(f"{prefix}: controlled formal generation requires a released asset package")

    if expected["g2"] in {"auto_run", "ready"} and expected["formal_generation"] != "allowed":
        errors.append(f"{prefix}: G2 {expected['g2']} requires formal_generation=allowed")
    if expected["g2"] == "ready" and expected["next_gate"] != "G2":
        errors.append(f"{prefix}: ready G2 must identify G2 as the current delivery gate")

    expected_events = expected["expected_events"] if isinstance(expected["expected_events"], list) else []
    forbidden_events = expected["forbidden_events"] if isinstance(expected["forbidden_events"], list) else []
    expected_event_set = {event for event in expected_events if isinstance(event, str)}
    forbidden_event_set = {event for event in forbidden_events if isinstance(event, str)}
    event_overlap = expected_event_set & forbidden_event_set
    if event_overlap:
        errors.append(f"{prefix}: events cannot be both expected and forbidden {sorted(event_overlap)}")

    def require_expected(event: str, reason: str) -> None:
        if event not in expected_event_set:
            errors.append(f"{prefix}.expected_events: {reason} requires {event}")

    def require_forbidden(event: str, reason: str) -> None:
        if event not in forbidden_event_set:
            errors.append(f"{prefix}.forbidden_events: {reason} requires {event}")

    mode_events = {
        "atomic": "ROUTE_ATOMIC",
        "direct": "ENTER_DIRECT",
        "guided": "ENTER_GUIDED",
        "controlled": "ENTER_CONTROLLED",
        "edit": "ENTER_EDIT",
    }
    if mode in mode_events:
        require_expected(mode_events[mode], f"workflow_mode={mode}")

    if expected["next_gate"] == "G0":
        require_expected("PRESENT_G0", "next_gate=G0")
        require_forbidden("BYPASS_G0", "next_gate=G0")
    if expected["next_gate"] == "G1":
        require_expected("PRESENT_G1", "next_gate=G1")
        require_forbidden("BYPASS_G1", "next_gate=G1")
        require_forbidden("USE_CANDIDATE_AS_RELEASE", "next_gate=G1")
    if expected["next_gate"] == "blocked":
        require_expected("BLOCK_WORK", "next_gate=blocked")
        require_forbidden("GENERATE_FORMAL_IMAGE", "next_gate=blocked")

    if expected["formal_generation"] in {"blocked", "not_applicable"}:
        if "GENERATE_FORMAL_IMAGE" in expected_event_set or "APPLY_EDIT" in expected_event_set:
            errors.append(f"{prefix}: blocked/not-applicable formal generation cannot schedule an image operation")
    if expected["formal_generation"] == "blocked":
        require_forbidden("GENERATE_FORMAL_IMAGE", "formal_generation=blocked")
    if "GENERATE_FORMAL_IMAGE" in expected_event_set:
        if expected["formal_generation"] != "allowed" or mode == "edit":
            errors.append(f"{prefix}: GENERATE_FORMAL_IMAGE requires allowed non-edit mode")
    if "APPLY_EDIT" in expected_event_set:
        if expected["formal_generation"] != "allowed" or mode != "edit":
            errors.append(f"{prefix}: APPLY_EDIT requires allowed edit mode")

    if expected["g2"] == "auto_run":
        require_expected("RUN_G2", "g2=auto_run")
        require_expected("APPLY_EDIT" if mode == "edit" else "GENERATE_FORMAL_IMAGE", "g2=auto_run")
    if expected["g2"] == "ready":
        require_expected("RUN_G2", "g2=ready")
        require_expected("DELIVER_G2", "g2=ready")
    if expected["g2"] == "blocked":
        require_expected("RUN_REPAIR", "g2=blocked")
        require_forbidden("DELIVER_G2", "g2=blocked")

    if mode == "atomic":
        require_forbidden("GENERATE_FORMAL_IMAGE", "atomic mode")
        require_forbidden("APPLY_EDIT", "atomic mode")
    if mode == "edit":
        for event in ("PRESENT_G0", "PRESENT_G1", "REQUEST_EXTRA_CONFIRMATION", "CHANGE_PRESERVED_FIELDS"):
            require_forbidden(event, "edit mode")

    if case_id in {"rollback-01", "route-fallback-01", "qa-01"}:
        if (mode, count, risk) != ("controlled", 2, 2):
            errors.append(f"{prefix}: hard-risk migration requires controlled/2/floor2")

    if case_id == "rollback-01":
        if expected["next_gate"] != "G0" or expected["standing_authorization"] != "out_of_scope":
            errors.append(f"{prefix}: rollback-01 must return to G0 with out-of-scope authorization")
        if expected["asset_release"] != "invalid" or expected["formal_generation"] != "blocked":
            errors.append(f"{prefix}: rollback-01 must invalidate release and block formal generation")
        require_expected("BLOCK_WORK", "rollback-01 rights scope change")
        require_forbidden("GENERATE_CANDIDATE_ASSETS", "rollback-01 rights scope change")
        require_forbidden("GENERATE_FORMAL_IMAGE", "rollback-01 rights scope change")

    if case_id in {"route-fallback-01", "qa-01"}:
        if expected["next_gate"] != "G1":
            errors.append(f"{prefix}: hard-risk repair must preserve G0 and continue at G1")
        if expected["asset_release"] != "pending_g1":
            errors.append(f"{prefix}: hard-risk repair requires pending_g1 assets")
        if expected["formal_generation"] != "blocked" or expected["g2"] != "not_ready":
            errors.append(f"{prefix}: hard-risk repair must block formal generation until G1")
        require_forbidden("RESTART_FROM_G0", f"{case_id} preserves effective G0")

    if case_id == "rights-01":
        require_expected("BLOCK_WORK", "rights-01 unresolved rights")
        require_forbidden("GENERATE_CANDIDATE_ASSETS", "rights-01 unresolved rights")
        require_forbidden("GENERATE_FORMAL_IMAGE", "rights-01 unresolved rights")

    if case_id == "control-floor-01":
        if (mode, count, risk, expected["next_gate"]) != ("controlled", 2, 2, "G1"):
            errors.append(f"{prefix}: control-floor-01 must remain controlled/2/floor2 at G1")
        require_forbidden("DOWNGRADE_BELOW_RISK_FLOOR", "control-floor-01")
    if case_id == "edit-exit-01":
        require_expected("EXIT_EDIT", "edit-exit-01")
        if mode == "edit":
            errors.append(f"{prefix}: edit-exit-01 must leave edit mode")
    if case_id == "idempotent-confirmation-01":
        require_forbidden("REQUEST_EXTRA_CONFIRMATION", "idempotent-confirmation-01")
        require_forbidden("PRESENT_G0", "idempotent-confirmation-01")
    if case_id == "field-invalidation-01":
        invalidated = set(validity["invalidate"]) if isinstance(validity, dict) else set()
        preserved = set(validity["preserve"]) if isinstance(validity, dict) else set()
        required_invalid = {
            "panel_2_text_budget",
            "panel_2_lettering_layout",
            "panel_2_prompt",
            "panel_2_formal_image",
            "panel_2_text_qa",
        }
        if invalidated != required_invalid:
            errors.append(f"{prefix}: field-invalidation-01 invalidation set must be text-only and exact")
        if not {"g1_effectiveness", "asset_release"} <= preserved:
            errors.append(f"{prefix}: field-invalidation-01 must preserve G1 effectiveness and asset release")
        if expected["next_gate"] != "G2" or expected["asset_release"] != "released":
            errors.append(f"{prefix}: field-invalidation-01 must continue to G2 with released assets")
        require_forbidden("RESTART_FROM_G0", "field-invalidation-01")
        require_forbidden("BYPASS_G1", "field-invalidation-01")
        require_forbidden("PRESENT_G0", "field-invalidation-01")
        require_forbidden("PRESENT_G1", "field-invalidation-01")
        require_forbidden("REQUEST_EXTRA_CONFIRMATION", "field-invalidation-01")
    if case_id == "invalidation-character-01":
        preserved = set(validity["preserve"]) if isinstance(validity, dict) else set()
        required_preserve = {
            "usagi_character_anchor",
            "chiikawa_character_anchor",
            "authorization_rights",
        }
        if not required_preserve <= preserved:
            errors.append(f"{prefix}: invalidation-character-01 must preserve Usagi, Chiikawa, and rights")
        invalidated = set(validity["invalidate"]) if isinstance(validity, dict) else set()
        allowed_invalid = {
            "hachiware_character_anchor",
            "hachiware_dependent_layouts",
            "asset_release",
            "formal_image",
        }
        if invalidated != allowed_invalid:
            errors.append(f"{prefix}: invalidation-character-01 must invalidate only Hachiware downstream")
    if case_id == "invalidation-unknown-01":
        if expected["next_gate"] != "blocked":
            errors.append(f"{prefix}: invalidation-unknown-01 must fail closed")
        require_forbidden("GUESS_UNKNOWN_DEPENDENCY", "invalidation-unknown-01")
    if case_id == "concurrent-write-01":
        if expected["next_gate"] != "blocked":
            errors.append(f"{prefix}: concurrent-write-01 must block on revision conflict")
        require_expected("REJECT_STALE_WRITE", "concurrent-write-01")
        require_forbidden("OVERWRITE_NEWER_REVISION", "concurrent-write-01")

    negative_contract = NEGATIVE_CASE_CONTRACTS.get(case_id)
    if negative_contract:
        state_keys = (
            "workflow_mode", "blocking_confirmations", "risk_floor", "next_gate",
            "standing_authorization", "formal_generation", "asset_release", "g2",
        )
        actual_state = tuple(expected[key] for key in state_keys)
        if actual_state != negative_contract["state"]:
            errors.append(
                f"{prefix}: negative-case state must be {negative_contract['state']}, "
                f"got {actual_state}"
            )
        required_expected = negative_contract["expected_events"]
        missing_expected = sorted(required_expected - expected_event_set)
        if missing_expected:
            errors.append(
                f"{prefix}.expected_events: missing negative-case events {missing_expected}"
            )
        required_forbidden = negative_contract["forbidden_events"]
        missing_forbidden = sorted(required_forbidden - forbidden_event_set)
        if missing_forbidden:
            errors.append(
                f"{prefix}.forbidden_events: missing negative-case events {missing_forbidden}"
            )
        provenance = set(expected["provenance_required"])
        missing_provenance = sorted(negative_contract["provenance"] - provenance)
        if missing_provenance:
            errors.append(
                f"{prefix}.provenance_required: missing negative-case evidence {missing_provenance}"
            )
        invalidated = set(validity["invalidate"]) if isinstance(validity, dict) else set()
        preserved = set(validity["preserve"]) if isinstance(validity, dict) else set()
        missing_invalidated = sorted(negative_contract["invalidate"] - invalidated)
        missing_preserved = sorted(negative_contract["preserve"] - preserved)
        if missing_invalidated:
            errors.append(
                f"{prefix}.effective_validity.invalidate: missing {missing_invalidated}"
            )
        if missing_preserved:
            errors.append(
                f"{prefix}.effective_validity.preserve: missing {missing_preserved}"
            )


def validate_fixture(data: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["root: expected an object"]

    required_root = {
        "skill",
        "version",
        "fixture_schema_version",
        "scope",
        "test_cases",
        "minimum_pass_rate",
        "notes",
    }
    missing = required_root - set(data)
    extra = set(data) - required_root
    if missing:
        errors.append(f"root: missing keys {sorted(missing)}")
    if extra:
        errors.append(f"root: unexpected keys {sorted(extra)}")

    if data.get("skill") != "build-image-fast":
        errors.append("root.skill: expected 'build-image-fast'")
    if data.get("version") != "5.3.0":
        errors.append("root.version: expected '5.3.0'")
    if data.get("fixture_schema_version") != "2.3.0":
        errors.append("root.fixture_schema_version: expected '2.3.0'")
    if not is_nonempty_string(data.get("scope")):
        errors.append("root.scope: expected a non-empty string")
    if not is_nonempty_string(data.get("notes")):
        errors.append("root.notes: expected a non-empty string")

    pass_rate = data.get("minimum_pass_rate")
    if not isinstance(pass_rate, (int, float)) or isinstance(pass_rate, bool) or not 0 <= pass_rate <= 1:
        errors.append("root.minimum_pass_rate: expected a number from 0 to 1")

    test_cases = data.get("test_cases")
    if not isinstance(test_cases, list) or not test_cases:
        errors.append("root.test_cases: expected a non-empty list")
        return errors

    ids: list[str] = []
    for index, case in enumerate(test_cases):
        prefix = f"test_cases[{index}]"
        if not isinstance(case, dict):
            errors.append(f"{prefix}: expected an object")
            continue
        required_case = {"id", "type", "category", "prompt", "expected"}
        missing_case = required_case - set(case)
        extra_case = set(case) - required_case
        if missing_case:
            errors.append(f"{prefix}: missing keys {sorted(missing_case)}")
        if extra_case:
            errors.append(f"{prefix}: unexpected keys {sorted(extra_case)}")

        case_id = case.get("id")
        if not is_nonempty_string(case_id):
            errors.append(f"{prefix}.id: expected a non-empty string")
            case_id = f"index-{index}"
        else:
            ids.append(case_id)

        if case.get("type") not in CASE_TYPES:
            errors.append(f"case {case_id}.type: invalid value {case.get('type')!r}")
        if not is_nonempty_string(case.get("category")):
            errors.append(f"case {case_id}.category: expected a non-empty string")
        if not is_nonempty_string(case.get("prompt")):
            errors.append(f"case {case_id}.prompt: expected a non-empty string")

        negative_contract = NEGATIVE_CASE_CONTRACTS.get(case_id)
        if negative_contract:
            if case.get("type") != "edge_case":
                errors.append(f"case {case_id}.type: negative fixture must be edge_case")
            if case.get("category") != negative_contract["category"]:
                errors.append(
                    f"case {case_id}.category: expected {negative_contract['category']!r}"
                )
            prompt = case.get("prompt") if isinstance(case.get("prompt"), str) else ""
            prompt_lower = prompt.lower()
            missing_tokens = sorted(
                token for token in negative_contract["prompt_tokens"]
                if token.lower() not in prompt_lower
            )
            if missing_tokens:
                errors.append(
                    f"case {case_id}.prompt: missing contract tokens {missing_tokens}"
                )

        validate_expected(case_id, case.get("expected"), errors)

        expected = case.get("expected")
        if isinstance(expected, dict) and case.get("type") == "should_not_trigger":
            if expected.get("workflow_mode") != "atomic":
                errors.append(f"case {case_id}: should_not_trigger requires atomic workflow_mode")

    duplicate_ids = sorted({case_id for case_id in ids if ids.count(case_id) > 1})
    if duplicate_ids:
        errors.append(f"root.test_cases: duplicate ids {duplicate_ids}")

    id_set = set(ids)
    missing_legacy = sorted(LEGACY_CASE_IDS - id_set)
    missing_v5 = sorted(REQUIRED_V5_CASE_IDS - id_set)
    if missing_legacy:
        errors.append(f"migration: missing V4 case ids {missing_legacy}")
    if missing_v5:
        errors.append(f"coverage: missing required V5 case ids {missing_v5}")

    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate build-image-fast test fixture schema and consistency only."
    )
    parser.add_argument(
        "fixture",
        nargs="?",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "test-prompts.json",
        help="Path to test-prompts.json (defaults to the skill fixture).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        data = json.loads(args.fixture.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"ERROR: fixture not found: {args.fixture}", file=sys.stderr)
        return 2
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot read fixture: {exc}", file=sys.stderr)
        return 2

    errors = validate_fixture(data)
    if errors:
        print(f"INVALID: {len(errors)} schema/consistency error(s)", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(
        f"VALID: {len(data['test_cases'])} contract fixtures; "
        f"schema={data['fixture_schema_version']}; version={data['version']}"
    )
    print("NOTE: fixture validation only; no LLM, image generation, QA scoring, or prompt execution ran.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
