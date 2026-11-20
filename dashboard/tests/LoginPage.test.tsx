import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import { session } from '@/api/client';
import { App } from '@/App';

import { fakeApi, makeUser, renderWithProviders } from './helpers';

function tokens(roles: Parameters<typeof makeUser>[0]) {
  return { access_token: 'a', refresh_token: 'r', expires_in: 900, user: makeUser(roles) };
}

describe('sign-in', () => {
  it('turns away reporter accounts and revokes the session it was given', async () => {
    const api = fakeApi({ 'POST /auth/login': tokens(['REPORTER']), 'POST /auth/logout': () => ({ status: 204 }) });
    renderWithProviders(<App />, { route: '/login' });

    await userEvent.type(screen.getByLabelText('Email or phone number'), '+254700000001');
    await userEvent.type(screen.getByLabelText('Password'), 'Passw0rd!');
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('The dashboard is for agency staff and administrators');
    expect(api.calls.map((c) => c.path)).toContain('/auth/logout');
    expect(session.access()).toBeNull();
  });

  it('shows the server message for wrong credentials', async () => {
    fakeApi({ 'POST /auth/login': () => ({ status: 401, body: { detail: 'Wrong phone/email or password.' } }) });
    renderWithProviders(<App />, { route: '/login' });
    await userEvent.type(screen.getByLabelText('Email or phone number'), 'x@example.org');
    await userEvent.type(screen.getByLabelText('Password'), 'nope1234');
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Wrong phone/email or password.');
  });

  it('sends visitors who are not signed in to the sign-in page', async () => {
    renderWithProviders(<App />, { route: '/trends' });
    expect(await screen.findByRole('heading', { name: 'Sign in to the TraceHealth dashboard' })).toBeInTheDocument();
  });
});
