# Laufende omakeyklack-Instanzen finden und beenden.
#
# Zum Einbinden gedacht (source), nicht zum Aufrufen. install.sh braucht
# das vor dem Neustart, uninstall.sh vor dem Loeschen.
#
# Warum nicht einfach "pkill -f omakeyklack": Die Skripte heissen selbst so
# - omakeyklack-uninstall etwa - und schoessen sich damit ab, bevor sie
# fertig sind. Getroffen werden darum nur Prozesse, die "omakeyklack" als
# eigenes Argument tragen. Das ist "python3 -m omakeyklack", aber kein
# Pfad, in dem der Name bloss vorkommt.

# Gibt die PIDs laufender Instanzen aus, eine je Zeile.
omakeyklack_instanzen() {
  local eintrag pid args a
  for eintrag in /proc/[0-9]*; do
    pid="${eintrag#/proc/}"
    [ "$pid" = "$$" ] && continue
    mapfile -d '' -t args < "$eintrag/cmdline" 2>/dev/null || continue
    for a in "${args[@]}"; do
      [ "$a" = "omakeyklack" ] && { echo "$pid"; break; }
    done
  done
}

# Beendet alle laufenden Instanzen. Gibt 0 zurueck, wenn danach keine mehr
# laeuft - auch dann, wenn es vorher schon keine gab.
omakeyklack_beenden() {
  local pids versuch
  mapfile -t pids < <(omakeyklack_instanzen)
  [ "${#pids[@]}" -gt 0 ] || return 0

  kill -TERM "${pids[@]}" 2>/dev/null || true
  echo "Laufende Instanz beendet (PID ${pids[*]})."

  # Bis zu drei Sekunden Zeit lassen: do_shutdown nimmt wayvibes mit, und
  # dessen Abbau darf nicht mitten hinein abgewuergt werden.
  for versuch in $(seq 1 30); do
    sleep 0.1
    mapfile -t pids < <(omakeyklack_instanzen)
    [ "${#pids[@]}" -eq 0 ] && return 0
  done

  echo "Eine Instanz reagierte nicht - beende sie hart."
  kill -KILL "${pids[@]}" 2>/dev/null || true
  sleep 0.3
  mapfile -t pids < <(omakeyklack_instanzen)
  [ "${#pids[@]}" -eq 0 ]
}
