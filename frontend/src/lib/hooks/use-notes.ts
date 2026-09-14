"use client";

/**
 * Consultation notes - the clinical record a doctor writes for a patient
 * against an appointment, and that the patient can read back.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { notesApi } from "@/lib/api/endpoints";
import { queryKeys } from "@/lib/query-keys";

export function useAppointmentNotes(
  appointmentId: number | null,
  enabled = true,
) {
  return useQuery({
    queryKey: queryKeys.notes.forAppointment(appointmentId ?? 0),
    queryFn: () => notesApi.forAppointment(appointmentId as number),
    enabled: enabled && appointmentId !== null,
  });
}

/** Doctors get the notes they wrote; patients get the notes about them. */
export function useMyNotes(enabled = true, limit = 50) {
  return useQuery({
    queryKey: queryKeys.notes.mine(),
    queryFn: () => notesApi.mine(limit),
    enabled,
  });
}

function useNotesInvalidator() {
  const queryClient = useQueryClient();
  return (appointmentId: number) => {
    void queryClient.invalidateQueries({
      queryKey: queryKeys.notes.forAppointment(appointmentId),
    });
    void queryClient.invalidateQueries({ queryKey: queryKeys.notes.mine() });
    // note_count is part of the appointment payload.
    void queryClient.invalidateQueries({
      queryKey: queryKeys.appointments.all,
    });
  };
}

export function useCreateNote() {
  const invalidate = useNotesInvalidator();

  return useMutation({
    mutationFn: ({
      appointmentId,
      body,
    }: {
      appointmentId: number;
      body: string;
    }) => notesApi.create(appointmentId, body),
    onSuccess: (note) => invalidate(note.appointment_id),
  });
}

export function useUpdateNote() {
  const invalidate = useNotesInvalidator();

  return useMutation({
    mutationFn: ({ noteId, body }: { noteId: number; body: string }) =>
      notesApi.update(noteId, body),
    onSuccess: (note) => invalidate(note.appointment_id),
  });
}

export function useDeleteNote() {
  const invalidate = useNotesInvalidator();

  return useMutation({
    mutationFn: ({
      noteId,
    }: {
      noteId: number;
      /** Needed to invalidate the right branch once the note is gone. */
      appointmentId: number;
    }) => notesApi.remove(noteId),
    onSuccess: (_result, variables) => invalidate(variables.appointmentId),
  });
}
