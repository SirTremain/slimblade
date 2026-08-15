use slimblade_image::{
    ACTIVE_LOOP_HOOK_PROBE, EXPERIMENT_ENTRY_PROBE, FirmwareIdentity, LATE_MARKER_PROBE,
    OFFICIAL_V449, POST_INIT_HOOK_PROBE, RECOVERY_CARRIER, RECOVERY_GUARD, RECOVERY_STUB,
    RESET_TRAMPOLINE, RUST_RESPONSE_PROBE, STARTUP_TRAMPOLINE, STEADY_LOOP_HOOK_PROBE,
    STOCK_HARNESS, USB_RECOVERY_PROBE, V449_DESCRIPTOR_PROBE, WIRED_LOOP_HOOK_PROBE,
};
use slimblade_protocol::NormalReport;

pub const FULL_RECOVERY_CONFIRMATION: &str = "ERASE-MARKER-RESET";

#[must_use]
pub fn late_marker_response_is_success(response: NormalReport) -> bool {
    response.command_byte() == 0x0e && response.as_bytes().get(2) == Some(&0x01)
}

#[must_use]
pub fn rust_response_is_success(response: NormalReport) -> bool {
    response.command_byte() == 0x0e
        && response.as_bytes().get(2) == Some(&0x01)
        && response.as_bytes().get(3) == Some(&0x58)
}

#[must_use]
pub fn post_init_arm_response_is_success(response: NormalReport) -> bool {
    response.command_byte() == 0x0e
        && response.as_bytes().get(2) == Some(&0x01)
        && response.as_bytes().get(3) == Some(&0xa3)
}

#[must_use]
pub fn wired_loop_arm_response_is_success(response: NormalReport) -> bool {
    response.command_byte() == 0x0e
        && response.as_bytes().get(2) == Some(&0x01)
        && response.as_bytes().get(3) == Some(&0xa5)
}

#[must_use]
pub fn active_loop_arm_response_is_success(response: NormalReport) -> bool {
    response.command_byte() == 0x0e
        && response.as_bytes().get(2) == Some(&0x01)
        && response.as_bytes().get(3) == Some(&0xa6)
}

#[must_use]
pub fn steady_loop_arm_response_is_success(response: NormalReport) -> bool {
    response.command_byte() == 0x0e
        && response.as_bytes().get(2) == Some(&0x01)
        && response.as_bytes().get(3) == Some(&0xa7)
}

#[must_use]
pub fn post_init_hook_state(response: NormalReport) -> Option<u8> {
    if response.command_byte() == 0x0f && response.as_bytes().get(2) == Some(&0x01) {
        response.as_bytes().get(3).copied()
    } else {
        None
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum FlashArtifact {
    OfficialV449,
    DescriptorProbe,
    RecoveryCarrier,
    ResetTrampoline,
    RecoveryStub,
    StartupTrampoline,
    RecoveryGuard,
    UsbRecoveryProbe,
    StockHarness,
    LateMarkerProbe,
    ExperimentEntryProbe,
    RustResponseProbe,
    PostInitHookProbe,
    WiredLoopHookProbe,
    ActiveLoopHookProbe,
    SteadyLoopHookProbe,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum PostFlashExpectation {
    Application { bcd_device: &'static str },
    ResidentLoader,
    UsbSilence,
}

impl FlashArtifact {
    #[must_use]
    pub const fn identity(self) -> FirmwareIdentity {
        match self {
            Self::OfficialV449 => OFFICIAL_V449,
            Self::DescriptorProbe => V449_DESCRIPTOR_PROBE,
            Self::RecoveryCarrier => RECOVERY_CARRIER,
            Self::ResetTrampoline => RESET_TRAMPOLINE,
            Self::RecoveryStub => RECOVERY_STUB,
            Self::StartupTrampoline => STARTUP_TRAMPOLINE,
            Self::RecoveryGuard => RECOVERY_GUARD,
            Self::UsbRecoveryProbe => USB_RECOVERY_PROBE,
            Self::StockHarness => STOCK_HARNESS,
            Self::LateMarkerProbe => LATE_MARKER_PROBE,
            Self::ExperimentEntryProbe => EXPERIMENT_ENTRY_PROBE,
            Self::RustResponseProbe => RUST_RESPONSE_PROBE,
            Self::PostInitHookProbe => POST_INIT_HOOK_PROBE,
            Self::WiredLoopHookProbe => WIRED_LOOP_HOOK_PROBE,
            Self::ActiveLoopHookProbe => ACTIVE_LOOP_HOOK_PROBE,
            Self::SteadyLoopHookProbe => STEADY_LOOP_HOOK_PROBE,
        }
    }

    #[must_use]
    pub fn confirmation_matches(self, confirmation: &str) -> bool {
        digest_matches_hex(self.identity().container_sha256, confirmation)
    }

    #[must_use]
    pub fn confirmation_sha256(self) -> String {
        digest_to_hex(self.identity().container_sha256)
    }

    #[must_use]
    pub const fn post_flash_expectation(self) -> PostFlashExpectation {
        match self {
            Self::OfficialV449 => PostFlashExpectation::Application { bcd_device: "0449" },
            Self::DescriptorProbe => PostFlashExpectation::Application { bcd_device: "0450" },
            Self::RecoveryCarrier => PostFlashExpectation::Application { bcd_device: "0451" },
            Self::ResetTrampoline => PostFlashExpectation::Application { bcd_device: "0452" },
            Self::StartupTrampoline => PostFlashExpectation::Application { bcd_device: "0453" },
            Self::RecoveryStub => PostFlashExpectation::ResidentLoader,
            Self::RecoveryGuard => PostFlashExpectation::UsbSilence,
            Self::UsbRecoveryProbe => PostFlashExpectation::Application { bcd_device: "0454" },
            Self::StockHarness => PostFlashExpectation::Application { bcd_device: "0455" },
            Self::LateMarkerProbe => PostFlashExpectation::Application { bcd_device: "0456" },
            Self::ExperimentEntryProbe => PostFlashExpectation::Application { bcd_device: "0457" },
            Self::RustResponseProbe => PostFlashExpectation::Application { bcd_device: "0458" },
            Self::PostInitHookProbe => PostFlashExpectation::Application { bcd_device: "0459" },
            Self::WiredLoopHookProbe => PostFlashExpectation::Application { bcd_device: "0460" },
            Self::ActiveLoopHookProbe => PostFlashExpectation::Application { bcd_device: "0461" },
            Self::SteadyLoopHookProbe => PostFlashExpectation::Application { bcd_device: "0462" },
        }
    }
}

#[must_use]
pub fn full_recovery_confirmation_matches(confirmation: &str) -> bool {
    confirmation == FULL_RECOVERY_CONFIRMATION
}

fn digest_matches_hex(digest: [u8; 32], confirmation: &str) -> bool {
    let bytes = confirmation.as_bytes();
    if bytes.len() != 64 {
        return false;
    }
    digest.into_iter().enumerate().all(|(index, byte)| {
        let offset = index * 2;
        bytes.get(offset).copied() == Some(hex_digit(byte >> 4_u8))
            && bytes.get(offset + 1).copied() == Some(hex_digit(byte & 0x0f))
    })
}

fn digest_to_hex(digest: [u8; 32]) -> String {
    let mut output = String::with_capacity(64);
    for byte in digest {
        output.push(char::from(hex_digit(byte >> 4_u8)));
        output.push(char::from(hex_digit(byte & 0x0f)));
    }
    output
}

const fn hex_digit(nibble: u8) -> u8 {
    if nibble < 10 {
        b'0' + nibble
    } else {
        b'a' + nibble - 10
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn carrier_flash_needs_exact_hash_confirmation() {
        assert!(!FlashArtifact::RecoveryCarrier.confirmation_matches("wrong"));
    }

    #[test]
    fn reset_trampoline_needs_exact_hash_confirmation() {
        assert!(!FlashArtifact::ResetTrampoline.confirmation_matches("wrong"));
    }

    #[test]
    fn recovery_stub_needs_exact_hash_confirmation() {
        assert!(!FlashArtifact::RecoveryStub.confirmation_matches("wrong"));
    }

    #[test]
    fn startup_trampoline_needs_exact_hash_confirmation() {
        assert!(!FlashArtifact::StartupTrampoline.confirmation_matches("wrong"));
    }

    #[test]
    fn recovery_guard_needs_exact_hash_confirmation() {
        assert!(!FlashArtifact::RecoveryGuard.confirmation_matches("wrong"));
        assert!(FlashArtifact::RecoveryGuard.confirmation_matches(
            "7bb3055bc1575bcb9ca4eab9ba2a83a3dbaba131e92cca78fffb18397cc2d19a"
        ));
    }

    #[test]
    fn full_recovery_needs_exact_action_confirmation() {
        assert!(!full_recovery_confirmation_matches("wrong"));
        assert!(full_recovery_confirmation_matches("ERASE-MARKER-RESET"));
    }

    #[test]
    fn usb_probe_needs_exact_hash_confirmation() {
        assert!(!FlashArtifact::UsbRecoveryProbe.confirmation_matches("wrong"));
        assert!(FlashArtifact::UsbRecoveryProbe.confirmation_matches(
            "3ce23e3b9af4a1e713bad622f56fc9055cb178ca1ec198c7556c1dee44169e5a"
        ));
    }

    #[test]
    fn stock_harness_needs_exact_hash_confirmation() {
        assert!(!FlashArtifact::StockHarness.confirmation_matches("wrong"));
        assert!(FlashArtifact::StockHarness.confirmation_matches(
            "cac3bab34545a2e20ad545af5b91c4a55db1c9cacfdcb0f45e4a348b65e3b356"
        ));
        assert_eq!(
            FlashArtifact::StockHarness.post_flash_expectation(),
            PostFlashExpectation::Application { bcd_device: "0455" }
        );
    }

    #[test]
    fn late_marker_probe_needs_exact_hash_confirmation() {
        assert!(!FlashArtifact::LateMarkerProbe.confirmation_matches("wrong"));
        assert!(FlashArtifact::LateMarkerProbe.confirmation_matches(
            "76669e150983725954fec510eb0c6717f84e08ef2a1a8ef3fb59cb49f7566905"
        ));
        assert_eq!(
            FlashArtifact::LateMarkerProbe.post_flash_expectation(),
            PostFlashExpectation::Application { bcd_device: "0456" }
        );
    }

    #[test]
    fn experiment_entry_probe_needs_exact_hash_confirmation() {
        assert!(!FlashArtifact::ExperimentEntryProbe.confirmation_matches("wrong"));
        assert!(FlashArtifact::ExperimentEntryProbe.confirmation_matches(
            "bc3275a95a0ebd4f3c12863ed2607d5f9ce026903ef19f145e177834f1a988b3"
        ));
        assert_eq!(
            FlashArtifact::ExperimentEntryProbe.post_flash_expectation(),
            PostFlashExpectation::Application { bcd_device: "0457" }
        );
    }

    #[test]
    fn rust_response_probe_needs_exact_hash_confirmation() {
        assert!(!FlashArtifact::RustResponseProbe.confirmation_matches("wrong"));
        assert!(FlashArtifact::RustResponseProbe.confirmation_matches(
            "93e939ffdf19a7d862108182528fac7d9b066e59fa853b21327bedd6260b14d4"
        ));
        assert_eq!(
            FlashArtifact::RustResponseProbe.post_flash_expectation(),
            PostFlashExpectation::Application { bcd_device: "0458" }
        );
    }

    #[test]
    fn post_init_hook_probe_needs_exact_hash_confirmation() {
        assert!(!FlashArtifact::PostInitHookProbe.confirmation_matches("wrong"));
        assert!(FlashArtifact::PostInitHookProbe.confirmation_matches(
            "133f5241efecc23c7cc2fffcc0fdb34c37f5a3f840362938c27a2bc5353c1de1"
        ));
        assert_eq!(
            FlashArtifact::PostInitHookProbe.post_flash_expectation(),
            PostFlashExpectation::Application { bcd_device: "0459" }
        );
    }

    #[test]
    fn wired_loop_hook_probe_needs_exact_hash_confirmation() {
        assert!(!FlashArtifact::WiredLoopHookProbe.confirmation_matches("wrong"));
        assert!(FlashArtifact::WiredLoopHookProbe.confirmation_matches(
            "61cf9ebc9b7739fbc586a6949a1dbca2f754f07b6e3e7ea16a4319c6d365bd87"
        ));
        assert_eq!(
            FlashArtifact::WiredLoopHookProbe.post_flash_expectation(),
            PostFlashExpectation::Application { bcd_device: "0460" }
        );
    }

    #[test]
    fn active_loop_hook_probe_needs_exact_hash_confirmation() {
        assert!(!FlashArtifact::ActiveLoopHookProbe.confirmation_matches("wrong"));
        assert!(FlashArtifact::ActiveLoopHookProbe.confirmation_matches(
            "bf7aab32e3c32b4bf3853a7c79de21e5818961fbeb70239c95b40db7d898d077"
        ));
        assert_eq!(
            FlashArtifact::ActiveLoopHookProbe.post_flash_expectation(),
            PostFlashExpectation::Application { bcd_device: "0461" }
        );
    }

    #[test]
    fn steady_loop_hook_probe_needs_exact_hash_confirmation() {
        assert!(!FlashArtifact::SteadyLoopHookProbe.confirmation_matches("wrong"));
        assert!(FlashArtifact::SteadyLoopHookProbe.confirmation_matches(
            "3defe9f5fda2ebaefb923fbe1c62fdd877345ccb75f6b1eec2604e731688d310"
        ));
        assert_eq!(
            FlashArtifact::SteadyLoopHookProbe.post_flash_expectation(),
            PostFlashExpectation::Application { bcd_device: "0462" }
        );
    }

    #[test]
    #[allow(
        clippy::expect_used,
        reason = "the fixed recorded response must parse for the assertion to be meaningful"
    )]
    fn late_marker_response_requires_command_and_success_status() {
        let response = NormalReport::parse(&[
            0x08, 0x0e, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x3e,
        ])
        .expect("recorded carrier response is valid");
        assert!(late_marker_response_is_success(response));
        assert!(!late_marker_response_is_success(NormalReport::command(
            0x0e
        )));
        assert!(!late_marker_response_is_success(NormalReport::command(
            0x0f
        )));
    }

    #[test]
    #[allow(
        clippy::expect_used,
        reason = "the fixed recorded response must parse for the assertion to be meaningful"
    )]
    fn rust_response_requires_signature_and_success_status() {
        let response = NormalReport::parse(&[
            0x08, 0x0e, 0x01, 0x58, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0xe6,
        ])
        .expect("fixed Rust response is valid");
        assert!(rust_response_is_success(response));
        assert!(!rust_response_is_success(NormalReport::command(0x0e)));
    }

    #[test]
    #[allow(
        clippy::expect_used,
        reason = "the fixed candidate responses must parse for the assertions to be meaningful"
    )]
    fn post_init_responses_require_exact_signatures() {
        let arm = NormalReport::parse(&[
            0x08, 0x0e, 0x01, 0xa3, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x9b,
        ])
        .expect("fixed arm response is valid");
        let state = NormalReport::parse(&[
            0x08, 0x0f, 0x01, 0x02, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x3b,
        ])
        .expect("fixed state response is valid");
        assert!(post_init_arm_response_is_success(arm));
        assert_eq!(post_init_hook_state(state), Some(2));
        assert!(!post_init_arm_response_is_success(state));
        assert_eq!(post_init_hook_state(arm), None);
    }

    #[test]
    #[allow(
        clippy::expect_used,
        reason = "the fixed corrected response must parse for the assertion to be meaningful"
    )]
    fn wired_loop_response_requires_exact_signature() {
        let arm = NormalReport::parse(&[
            0x08, 0x0e, 0x01, 0xa5, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x99,
        ])
        .expect("fixed corrected response is valid");
        assert!(wired_loop_arm_response_is_success(arm));
        assert!(!post_init_arm_response_is_success(arm));
    }

    #[test]
    #[allow(
        clippy::expect_used,
        reason = "the fixed active-loop response must parse for the assertion to be meaningful"
    )]
    fn active_loop_response_requires_exact_signature() {
        let arm = NormalReport::parse(&[
            0x08, 0x0e, 0x01, 0xa6, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x98,
        ])
        .expect("fixed active-loop response is valid");
        assert!(active_loop_arm_response_is_success(arm));
        assert!(!wired_loop_arm_response_is_success(arm));
    }

    #[test]
    #[allow(
        clippy::expect_used,
        reason = "the fixed steady-loop response must parse for the assertion to be meaningful"
    )]
    fn steady_loop_response_requires_exact_signature() {
        let arm = NormalReport::parse(&[
            0x08, 0x0e, 0x01, 0xa7, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x97,
        ])
        .expect("fixed steady-loop response is valid");
        assert!(steady_loop_arm_response_is_success(arm));
        assert!(!active_loop_arm_response_is_success(arm));
    }
}
