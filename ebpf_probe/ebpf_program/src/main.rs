#![no_std]
#![no_main]

use aya_ebpf::{
    bindings::xdp_action,
    macros::xdp,
    programs::XdpContext,
};

/// XDP program. Returns XDP_PASS for every packet.
/// Does not read packet data and does not drop traffic.
#[xdp]
pub fn xdp_firewall(_ctx: XdpContext) -> u32 {
    xdp_action::XDP_PASS
}

#[panic_handler]
fn panic(_info: &core::panic::PanicInfo) -> ! {
    unsafe { core::hint::unreachable_unchecked() }
}
