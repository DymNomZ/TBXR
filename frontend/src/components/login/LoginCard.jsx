import LoginForm from './LoginForm'

function LoginCard() {
  return (
    <div className="w-full max-w-md rounded-[28px] border border-slate-200 bg-white p-8 shadow-soft">
      <div className="mb-8">
        <p className="text-xs font-semibold uppercase tracking-[0.3em] text-slate-500">
          TB-XR
        </p>
        <h1 className="mt-4 text-4xl font-semibold text-slate-950">Sign in</h1>
        <p className="mt-3 text-sm leading-6 text-slate-600">
          Access the teleradiology platform for patient image uploads and review.
        </p>
      </div>

      <LoginForm />
    </div>
  )
}

export default LoginCard
