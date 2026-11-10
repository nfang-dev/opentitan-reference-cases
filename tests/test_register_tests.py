"""Tests for the register-test tooling (csr/) that do not need a simulator."""

import importlib.util
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "csr"))

import gen_harness  # noqa: E402
import regmodel  # noqa: E402

TOP = """
module foo
  import foo_pkg::*;
  import foo_reg_pkg::*;
#(
  parameter logic [NumAlerts-1:0] AlertAsyncOn = {NumAlerts{1'b1}}
) (
  input  logic                clk_i,
  input  logic                clk_aon_i,
  input  logic                rst_ni,
  input  tlul_pkg::tl_h2d_t   tl_i,
  output tlul_pkg::tl_d2h_t   tl_o,
  // Alerts
  input  prim_alert_pkg::alert_rx_t [NumAlerts-1:0] alert_rx_i,
  output prim_alert_pkg::alert_tx_t [NumAlerts-1:0] alert_tx_o,
  input  lc_ctrl_pkg::lc_tx_t lc_escalate_en_i,
  input        [NumIOs-1:0]   cio_in_i,  // pads
  output logic                intr_o
);
endmodule
"""
PACKAGES = {"foo_reg_pkg": "parameter int NumAlerts = 1;", "foo_pkg": "parameter int NumIOs = 4;"}

REG_TOP = """
  prim_subreg #(
    .DW      (1),
    .SwAccess(prim_subreg_pkg::SwAccessRW),
    .RESVAL  (1'h0),
    .Mubi    (1'b0)
  ) u_ctrl_en (
  assign alert_test_gated_we = alert_test_we && alert_test_regwen_qs;
"""
MODEL = {"registers": [{"name": "CTRL", "offset": 0, "hwext": False, "shadowed": False,
                        "regwen": None, "tags": [],
                        "fields": [{"name": "EN", "lsb": 0, "width": 1, "swaccess": "rw",
                                    "hwaccess": "hro", "resval": 0, "tags": []},
                                   {"name": "MODE", "lsb": 1, "width": 2, "swaccess": "rw",
                                    "hwaccess": "hro", "resval": 0, "tags": []}]}]}


class HarnessTest(unittest.TestCase):
    def test_ports(self):
        imports, ports = gen_harness.parse_ports(TOP, "foo")
        self.assertEqual(imports, ["foo_pkg", "foo_reg_pkg"])
        self.assertEqual([p.name for p in ports],
                         ["clk_i", "clk_aon_i", "rst_ni", "tl_i", "tl_o", "alert_rx_i",
                          "alert_tx_o", "lc_escalate_en_i", "cio_in_i", "intr_o"])
        alert = ports[5]
        self.assertEqual((alert.type, alert.dims), ("prim_alert_pkg::alert_rx_t", "[NumAlerts-1:0]"))

    def test_harness(self):
        sv, clocks_resets = gen_harness.harness("foo", TOP, PACKAGES)
        self.assertEqual(clocks_resets, ["clk_i", "clk_aon_i", "rst_ni"])
        self.assertIn(".alert_rx_i ({foo_reg_pkg::NumAlerts{prim_alert_pkg::ALERT_RX_DEFAULT}})", sv)
        self.assertIn(".lc_escalate_en_i (lc_ctrl_pkg::Off)", sv)
        self.assertIn(".cio_in_i ('0)", sv)
        self.assertIn(".tl_i (tl_h2d)", sv)
        self.assertIn(".intr_o ()", sv)
        self.assertIn("prim_alert_pkg::alert_tx_t [foo_reg_pkg::NumAlerts-1:0] alert_tx_o_w;", sv)
        self.assertIn("assign alert_o = alert_any_alert_tx_o;", sv)


class ModelTest(unittest.TestCase):
    def test_exclusions_follow_opentitan_encoding(self):
        tags = ["excl:CsrNonInitTests:CsrExclWrite"]
        self.assertTrue(regmodel.excluded(tags, "CsrRwTest", regmodel.WRITE))
        self.assertFalse(regmodel.excluded(tags, "CsrHwResetTest", regmodel.INIT_CHECK))
        self.assertFalse(regmodel.excluded(tags, "CsrRwTest", regmodel.WRITE_CHECK))
        everything = ["excl:CsrAllTests:CsrExclAll"]
        self.assertTrue(regmodel.excluded(everything, "CsrHwResetTest", regmodel.INIT_CHECK))

    @unittest.skipUnless(os.environ.get("OPENTITAN_DIR")
                         and (Path(os.environ["OPENTITAN_DIR"]) / "util/reggen").is_dir()
                         and importlib.util.find_spec("hjson"),
                         "needs an OpenTitan checkout with util/ and reggen's dependencies")
    def test_uart_model(self):
        model = regmodel.load(Path(os.environ["OPENTITAN_DIR"]), "hw/ip/uart/data/uart.hjson")
        names = [r["name"] for r in model["registers"]]
        self.assertIn("CTRL", names)
        self.assertEqual(model["registers"][0]["tags"], ["excl:CsrAllTests:CsrExclAll"])


class MutationTest(unittest.TestCase):
    def test_mutations(self):
        import run
        text, desc = run.mutate(REG_TOP, MODEL, "resval")
        self.assertIn(".RESVAL  (1'h1)", text)
        self.assertIn("CTRL.EN", desc)
        text, _ = run.mutate(REG_TOP, MODEL, "access")
        self.assertIn("SwAccessRO)", text)
        text, _ = run.mutate(REG_TOP, MODEL, "regwen")
        self.assertIn("assign alert_test_gated_we = alert_test_we;", text)

    def test_lock_mutation(self):
        import run
        locked = {"registers": [dict(MODEL["registers"][0], name="WDOG_CTRL", regwen="WDOG_REGWEN")]}
        plain = "  assign wdog_ctrl_gated_we = wdog_ctrl_we & wdog_regwen_qs;\n"
        text, desc = run.mutate(plain, locked, "lock")
        self.assertIn("assign wdog_ctrl_gated_we = wdog_ctrl_we;", text)
        self.assertIn("WDOG_REGWEN", desc)
        cdc = ("  ) u_wdog_ctrl_cdc (\n    .src_regwen_i (wdog_regwen_qs),\n    .src_we_i (x)\n  );\n"
               "  ) u_other_cdc (\n    .src_regwen_i (wdog_regwen_qs),\n  );\n")
        text, _ = run.mutate(cdc, locked, "lock")
        self.assertEqual(text.count(".src_regwen_i (1'b1)"), 1)
        self.assertIn("u_other_cdc (\n    .src_regwen_i (wdog_regwen_qs)", text)
        with self.assertRaises(run.NotApplicable):
            run.mutate(plain, MODEL, "lock")


if __name__ == "__main__":
    unittest.main()
