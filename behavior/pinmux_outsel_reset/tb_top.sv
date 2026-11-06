// Copyright 2026 Nan Fang
// SPDX-License-Identifier: Apache-2.0
//
// Harness for the case 001 behavior check: the Earl Grey pinmux with the pad configuration of
// chip_earlgrey_asic, its registers reached through a one-request-at-a-time port, and every other
// input held at an inactive value.

module tb_top
  import top_earlgrey_pkg::*;
  import prim_pad_wrapper_pkg::*;
(
  input  logic                                     clk_i,
  input  logic                                     rst_ni,
  input  logic                                     clk_aon_i,
  input  logic                                     rst_aon_ni,

  // Register access. A request is accepted on a rising clock edge while reg_req_i and reg_gnt_o
  // are both 1; the response is valid while reg_rvalid_o is 1.
  input  logic                                     reg_req_i,
  input  logic                                     reg_we_i,
  input  logic [pinmux_reg_pkg::BlockAw-1:0]       reg_addr_i,
  input  logic [31:0]                              reg_wdata_i,
  output logic                                     reg_gnt_o,
  output logic                                     reg_rvalid_o,
  output logic [31:0]                              reg_rdata_o,
  output logic                                     reg_error_o,

  // Life-cycle enables: 1 drives On, 0 drives Off.
  input  logic                                     lc_hw_debug_en_i,
  input  logic                                     lc_dft_en_i,
  // From the power manager.
  input  logic                                     strap_en_i,
  input  logic                                     sleep_en_i,

  // Peripheral side of the muxed outputs.
  input  logic [pinmux_reg_pkg::NMioPeriphOut-1:0] periph_to_mio_i,
  input  logic [pinmux_reg_pkg::NMioPeriphOut-1:0] periph_to_mio_oe_i,

  // Pad side of the muxed I/Os.
  input  logic [pinmux_reg_pkg::NMioPads-1:0]      mio_in_i,
  output logic [pinmux_reg_pkg::NMioPads-1:0]      mio_out_o,
  output logic [pinmux_reg_pkg::NMioPads-1:0]      mio_oe_o,

  // Fatal alert (bus integrity error), positive rail.
  output logic                                     alert_o
);

  // Pad indices and PinmuxTargetCfg, extracted unchanged from chip_earlgrey_asic.sv by run.py.
  `include "pinmux_target_cfg.svh"

  // Register requests, with bus integrity added as a real bus host would.
  tlul_pkg::tl_h2d_t tl_h2d_raw, tl_h2d;
  tlul_pkg::tl_d2h_t tl_d2h;

  always_comb begin
    tl_h2d_raw           = tlul_pkg::TL_H2D_DEFAULT;
    tl_h2d_raw.a_valid   = reg_req_i;
    tl_h2d_raw.a_opcode  = reg_we_i ? tlul_pkg::PutFullData : tlul_pkg::Get;
    tl_h2d_raw.a_size    = 2'd2;
    tl_h2d_raw.a_mask    = 4'hf;
    tl_h2d_raw.a_address = 32'(reg_addr_i);
    tl_h2d_raw.a_data    = reg_we_i ? reg_wdata_i : 32'h0;
    tl_h2d_raw.d_ready   = 1'b1;
  end

  tlul_cmd_intg_gen u_cmd_intg_gen (
    .tl_i (tl_h2d_raw),
    .tl_o (tl_h2d)
  );

  assign reg_gnt_o    = tl_d2h.a_ready;
  assign reg_rvalid_o = tl_d2h.d_valid;
  assign reg_rdata_o  = tl_d2h.d_data;
  assign reg_error_o  = tl_d2h.d_error;

  prim_alert_pkg::alert_tx_t [pinmux_reg_pkg::NumAlerts-1:0] alert_tx;
  assign alert_o = alert_tx[0].alert_p;

  pinmux #(
    .TargetCfg (PinmuxTargetCfg)
  ) u_pinmux (
    .clk_i,
    .rst_ni,
    .rst_sys_ni                  (rst_ni),
    .scanmode_i                  (prim_mubi_pkg::MuBi4False),
    .clk_aon_i,
    .rst_aon_ni,
    .pin_wkup_req_o              (),
    .usb_wkup_req_o              (),
    .sleep_en_i,
    .strap_en_i,
    .strap_en_override_i         (1'b0),
    .lc_dft_en_i                 (lc_dft_en_i ? lc_ctrl_pkg::On : lc_ctrl_pkg::Off),
    .lc_hw_debug_clr_i           (lc_ctrl_pkg::Off),
    .lc_hw_debug_en_i            (lc_hw_debug_en_i ? lc_ctrl_pkg::On : lc_ctrl_pkg::Off),
    .lc_check_byp_en_i           (lc_ctrl_pkg::Off),
    .lc_escalate_en_i            (lc_ctrl_pkg::Off),
    .pinmux_hw_debug_en_o        (),
    .dft_strap_test_o            (),
    .dft_hold_tap_sel_i          (1'b0),
    .lc_jtag_o                   (),
    .lc_jtag_i                   (jtag_pkg::JTAG_RSP_DEFAULT),
    .rv_jtag_o                   (),
    .rv_jtag_i                   (jtag_pkg::JTAG_RSP_DEFAULT),
    .dft_jtag_o                  (),
    .dft_jtag_i                  (jtag_pkg::JTAG_RSP_DEFAULT),
    .usbdev_dppullup_en_i        (1'b0),
    .usbdev_dnpullup_en_i        (1'b0),
    .usb_dppullup_en_o           (),
    .usb_dnpullup_en_o           (),
    .usbdev_suspend_req_i        (1'b0),
    .usbdev_wake_ack_i           (1'b0),
    .usbdev_bus_not_idle_o       (),
    .usbdev_bus_reset_o          (),
    .usbdev_sense_lost_o         (),
    .usbdev_wake_detect_active_o (),
    .tl_i                        (tl_h2d),
    .tl_o                        (tl_d2h),
    .alert_rx_i                  ({pinmux_reg_pkg::NumAlerts{prim_alert_pkg::ALERT_RX_DEFAULT}}),
    .alert_tx_o                  (alert_tx),
    .periph_to_mio_i,
    .periph_to_mio_oe_i,
    .mio_to_periph_o             (),
    .periph_to_dio_i             ('0),
    .periph_to_dio_oe_i          ('0),
    .dio_to_periph_o             (),
    .mio_attr_o                  (),
    .mio_out_o,
    .mio_oe_o,
    .mio_in_i,
    .dio_attr_o                  (),
    .dio_out_o                   (),
    .dio_oe_o                    (),
    .dio_in_i                    ('0)
  );

endmodule
