# Mandatory questions

## Campaign

1. **Which repository and revision should this campaign use?** (`id: source`)
   - Answer: `https://github.com/openssl/openssl.git`,
     `0ffaa24c6148514fa77f76a48ae48852df7be9e7`

2. **Should this campaign port the C implementation to Rust, or create safe
   Rust wrappers?** (`id: objective`)
   - Answer: `port`

3. **What should this campaign target: a named subset of subsystems, or a named
   subset of functions and types, or the whole target repo? You can define them
   now or we can brainstorm them during the live session. You can also let the
   orchestrator decide.** (`id: scope`)
   - Answer: named libssl types and functions: the imported type closure, the
     imported symbols required by target layers L0 through L2, and the three god
     objects listed under Selection below. Implementation paths are `ssl/` plus the
     headers outside it that libssl implements; derive the public headers from the
     wavefront configuration.

4. **Which model and billing should do the translation work?**
   (`id: translate-agent`)
   - Answer: ask me, showing the supported providers and models; `subscription`
     billing

5. **Do you want agentic review after translated work lands? If so, which
   model and billing should perform each review?** (`id: review-agent`)
   - Answer: `no`

6. **Should I run fully autonomously end to end?** (`id: autonomy`)
   - Answer: `yes`, once the campaign brief is approved

# Optional questions

Unanswered optional questions use their defaults.

## Campaign execution

7. **Should the campaign use the default batching and parallelism settings, or
   customize them?** (`id: workload`)
   - Answer: defaults except `max-types: 1`; parallelism is orchestrator's choice

8. **What batch caps should review agents use? We recommend the same caps as
   translation by default.** (`id: review-workload`)
   - Answer: not applicable

# Benchmark recording questions

13. **Where and in what format should results be recorded?** (`id: results`)
    - Answer: `/target/crustify/results.md`, standard template

# Additional instructions

## Setup

Run Phase 1 end to end. Pre-authored `build.json` and `wavefront-config.json` sit beside
this task in `/opt/crustify/examples/crustify/openssl/libssl-port/` and may be copied
from there. Emit `subsystems.json` after the campaign-wide oracle target is populated.
Skip toolchain installation when the required tools are already installed.

Raw `void` and `string` lifetime discovery is required preparation owned by the
orchestrator. It is not a user-facing sub-campaign.

## Selection

The imported type closure contains these established selections:

- layer 0: `SHAstate_st`, `MD5state_st`, `ossl_param_st`, `buf_mem_st`,
  `ring_buf`, `pollfd`, `ossl_dispatch_st`, `SHA512state_st`, `wpacket_st`,
  `SHA256state_st`, `OSSL_TIME`, `evp_keymgmt_st`, `evp_pkey_ctx_st`,
  `evp_cipher_st`, `ossl_provider_st`, `evp_md_st`, `ossl_lib_ctx_st`,
  `evp_pkey_st`, `evp_kdf_st`, `evp_mac_st`, `evp_cipher_ctx_st`, `bio_st`,
  `lhash_st`, `bio_method_st`, `err_state_st`, `stack_st`, `comp_method_st`,
  `conf_imodule_st`, `ct_policy_eval_ctx_st`, `evp_md_ctx_st`,
  `evp_rand_ctx_st`, `ossl_algorithm_st`, `PACKET`, `pthread_mutex_t`,
  `evp_kdf_ctx_st`, `evp_mac_ctx_st`, `CRYPTO_REF_COUNT`, `ASN1_VALUE_st`,
  `crypto_mutex_st`, `engine_st`;
- layer 1: `ssl_comp_st`, `x509_st`, `dh_st`, `X509_name_st`,
  `stack_st_SCT`, `stack_st_SSL_COMP`.

The imported symbol selection required by target layers L0 through L2 is:

- `CRYPTO_free`, `__assert_fail`, `memcpy`, `memset`, `CRYPTO_malloc`,
  `CRYPTO_zalloc`, `strlen`, `memcmp`, `__errno_location`,
  `OPENSSL_LH_COMPFUNC`, `OPENSSL_LH_DOALL_FUNCARG`,
  `OPENSSL_LH_DOALL_FUNC`, `OPENSSL_LH_HASHFUNC`, `OPENSSL_strcasecmp`,
  `CRYPTO_realloc_array`, `strcmp`, `memchr`, `ossl_quic_vlint_encode_len`,
  `strspn`, `BIO_closesocket`, `OBJ_sn2nid`, `OBJ_ln2nid`, `ossl_isdigit`,
  `ossl_ctype_check`, `write`, `read`, `BIO_fd_non_fatal_error`;
- `ERR_new`, `ERR_set_debug`, `ossl_assert_int`, `CRYPTO_memdup`,
  `ossl_time_now`, `ERR_pop_to_mark`, `ossl_ticks2time`, `ERR_set_mark`,
  `ossl_time_compare`, `CRYPTO_realloc`, `ossl_time2ticks`, `ossl_time_add`;
- `PACKET_remaining`, `WPACKET_put_bytes__`, `BIO_ctrl`, `PACKET_data`,
  `OPENSSL_sk_num`, `OPENSSL_sk_value`, `WPACKET_sub_memcpy__`,
  `PACKET_buf_init`, `PACKET_get_net_2`, `PACKET_get_1`, `WPACKET_memcpy`,
  `OPENSSL_sk_push`, `WPACKET_get_total_written`,
  `PACKET_get_length_prefixed_2`, `RAND_bytes_ex`, `EVP_MD_CTX_new`,
  `EVP_MD_get_size`, `OSSL_PARAM_construct_end`, `BIO_puts`,
  `PACKET_get_length_prefixed_1`, `PACKET_get_quic_vlint`,
  `ossl_time_is_zero`, `ossl_time_zero`, `PACKET_forward`,
  `PACKET_get_bytes`, `WPACKET_quic_write_vlint`, `BIO_indent`,
  `ossl_time_infinite`, `WPACKET_allocate_bytes`.

The god-object selection is `record_layer_st`, `quic_stream_st`, and
`ssl_session_st`, including their transitive closure.

## Recording

The orchestrator derives internal waves and schedule files from these selections.
Record token-derived cost, the sub-campaign branch's diff, and the deterministic
`crustify <workdir> audit unsafe` scan after the sub-campaign completes.
