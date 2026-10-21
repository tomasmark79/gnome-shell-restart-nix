
/* Native data only: external shortcut owners survive complete JS replacement. */
static char *tgnome_external_accelerators;

/**
 * shell_global_tgnome_get_external_accelerators:
 * @global: the process-owned Shell global
 *
 * Returns: (transfer none): serialized native shortcut IDs, owners and modes
 */
const char *
shell_global_tgnome_get_external_accelerators (ShellGlobal *global)
{
  (void) global;
  return tgnome_external_accelerators ? tgnome_external_accelerators : "[]";
}

/**
 * shell_global_tgnome_set_external_accelerators:
 * @global: the process-owned Shell global
 * @records: serialized shortcut registration metadata, with no JS references
 */
void
shell_global_tgnome_set_external_accelerators (ShellGlobal *global, const char *records)
{
  (void) global;
  g_free (tgnome_external_accelerators);
  tgnome_external_accelerators = g_strdup (records);
}
