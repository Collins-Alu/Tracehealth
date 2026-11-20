/**
 * Photos for queued reports.
 *
 * The camera and gallery return files in a CACHE folder that Android may
 * clear when storage runs low. A queued report must survive that, so its
 * photo is copied into the app's private DOCUMENT folder until it is sent.
 */
import { Directory, File, Paths } from 'expo-file-system';

const FOLDER = 'queued-photos';

function folder(): Directory {
  const dir = new Directory(Paths.document, FOLDER);
  if (!dir.exists) dir.create({ intermediates: true, idempotent: true });
  return dir;
}

/** Copy a picked photo into permanent storage; returns the new file URI. */
export async function persistPhoto(sourceUri: string, clientReportId: string): Promise<string> {
  const destination = new File(folder(), `${clientReportId}.jpg`);
  if (destination.exists) destination.delete();
  await new File(sourceUri).copy(destination);
  return destination.uri;
}

export async function deletePhoto(uri: string): Promise<void> {
  const file = new File(uri);
  if (file.exists) file.delete();
}
