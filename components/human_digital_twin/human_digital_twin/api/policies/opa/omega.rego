
package omega
default allow_export = false
allow_export {
  some e
  e := input.resource.extension[_]
  e.url == "https://socioprophet.dev/ext/kfs-eval"
  e.valueCoding.code == "TRUSTED"
  m_cgt := e.extension[_].valueDecimal
  input.consent.allowed == true
  m_cgt >= 0.75
}
