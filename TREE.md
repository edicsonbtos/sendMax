# SENDMAX-BOT — Estructura del repo (TREE)

> Foto del mapa del proyecto para onboarding, handoff y debugging rápido.
SENDMAX-BOT/
├─ .env
├─ .gitignore
├─ alembic.ini
├─ requirements.txt
├─ pyvenv.cfg
├─ .venv/
├─ pycache/
├─ alembic/
│ ├─ env.py
│ ├─ script.py.mako
│ ├─ README
│ ├─ pycache/
│ └─ versions/
│ ├─ pycache/
│ ├─ b71a73ee4d14_create_users.py
│ ├─ 7fd3eec5ddbb_create_rates_tables.py
│ ├─ 1b0d81fcbce5_add_is_verified_to_p2p_country_prices.py
│ ├─ 8249dc838371_create_orders.py
│ ├─ 2c20eda69bd2_create_orders_public_id_sequence.py
│ ├─ 4876012249fd_add_dest_payment_proof_to_orders.py
│ ├─ c525e594bdd5_add_cancel_reason_to_orders.py
│ ├─ 47c816e9a216_create_wallets_ledger_withdrawals.py
│ ├─ 3c3f537e3f23_add_profit_usdt_to_orders.py
│ ├─ e62522510952_extend_withdrawals_for_fiat_payout_.py
│ ├─ 1f_hotfix_withdrawals_fiat_hotfix_.py
│ ├─ 1f2_withdrawals_fiat_cols_hotfix_.py
│ └─ hotfix_20260129160557_withdrawals_fiat_cols_hotfix_.py
├─ src/
│ ├─ init.py
│ ├─ main.py
│ ├─ rates_scheduler.py
│ ├─ rates_generator.py
│ ├─ tools/
│ │ ├─ audit_commissions.py
│ │ ├─ audit_wallet.py
│ │ ├─ env_diag.py
│ │ ├─ run.log
│ │ ├─ self_test.py
│ │ └─ sql_check.py
│ ├─ config/
│ │ ├─ settings.py
│ │ └─ logging.py
│ ├─ integrations/
│ │ ├─ binance_p2p.py
│ │ └─ p2p_config.py
│ ├─ db/
│ │ ├─ init.py
│ │ ├─ connection.py
│ │ └─ repositories/
│ │ ├─ init.py
│ │ ├─ users_repo.py
│ │ ├─ rates_repo.py
│ │ ├─ rates_baseline_repo.py
│ │ ├─ orders_repo.py
│ │ ├─ operator_summary_repo.py
│ │ ├─ referrals_repo.py
│ │ ├─ wallet_repo.py
│ │ └─ withdrawals_repo.py
│ └─ telegram_app/
│ ├─ init.py
│ ├─ bot.py
│ ├─ flows/
│ │ ├─ registration_flow.py
│ │ ├─ new_order_flow.py
│ │ ├─ payment_methods_flow.py
│ │ ├─ withdrawal_flow.py
│ │ ├─ withdrawal_flow.py.bak
│ │ └─ debug_new_order_flow.py
│ ├─ handlers/
│ │ ├─ init.py
│ │ ├─ start.py
│ │ ├─ menu.py
│ │ ├─ health.py
│ │ ├─ rates.py
│ │ ├─ rates_more.py
│ │ ├─ payment_methods.py
│ │ ├─ summary.py
│ │ ├─ referrals.py
│ │ ├─ wallet.py
│ │ ├─ admin_panel.py
│ │ ├─ admin_rates.py
│ │ ├─ admin_orders.py
│ │ ├─ admin_media_router.py
│ │ ├─ admin_paid_dm.py
│ │ ├─ admin_chatid.py
│ │ ├─ admin_alert_test.py
│ │ ├─ admin_withdrawals.py
│ │ ├─ admin_withdrawals.py.bak
│ │ ├─ debug_callbacks.py
│ │ ├─ ephemeral_cleanup.py
│ │ └─ group_media_probe.py
│ └─ ui/
│ ├─ init.py
│ ├─ keyboards.py
│ ├─ inline_buttons.py
│ ├─ routes_popular.py
│ ├─ rates_buttons.py
│ ├─ referrals_keyboards.py
│ └─ admin_keyboards.py
├─ generate_rates_once.py
├─ 2c20eda69bd2_create_orders_public_id_sequence.py (script suelto en raíz)
├─ audit_order.py
├─ audit_raw.py
├─ check_debug.py
├─ check_last_rate_versions.py
├─ check_orders_cols.py
├─ check_p2p_columns.py
├─ check_route_rates_counts.py
├─ check_seq.py
├─ check_tables.py
├─ check_users_columns.py
├─ create_seq.py
├─ debug_new_order_regex.py
├─ fix_alembic_version.py
├─ fix_env.py
├─ fix_id.py
├─ get_group_chat_id.py
├─ hotfix_withdrawals_alter.py
├─ inspect_wallet_withdrawals.py
├─ inspect_withdrawals_cols.py
├─ inspect_withdrawals_pg.py
├─ patch_notification.py
├─ seed_wallets.py
├─ set_alembic_version.py
├─ test_ars_no_method.py
├─ test_binance_buy_sell.py
├─ test_binance.py
└─ test_rates_pipeline.py

