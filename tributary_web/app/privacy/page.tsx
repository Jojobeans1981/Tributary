import Link from "next/link";

export default function PrivacyPage() {
  return (
    <div className="bg-mist min-h-screen">
      <div className="max-w-3xl mx-auto p-6">
        <Link
          href="/dashboard"
          className="text-current text-sm hover:underline mb-6 inline-block"
        >
          &larr; Back to dashboard
        </Link>

        <h1 className="font-display text-abyss text-3xl font-bold mb-6">
          TRIBUTARY Privacy Policy
        </h1>

        <div className="bg-chalk rounded-card shadow-card p-6 border border-pebble text-sm text-slate space-y-4">
          <section>
            <h2 className="font-display text-abyss text-lg font-bold mb-2">
              1. Overview
            </h2>
            <p>
              TRIBUTARY is a community matching platform for K-12 literacy
              professionals, operated by Upstream Literacy. This privacy policy
              describes how we collect, use, and protect your personal
              information in compliance with the Family Educational Rights and
              Privacy Act (FERPA), 20 U.S.C. &sect; 1232g; 34 CFR Part 99.
            </p>
          </section>

          <section>
            <h2 className="font-display text-abyss text-lg font-bold mb-2">
              2. Information We Collect
            </h2>
            <p>We collect the following categories of information:</p>
            <ul className="list-disc ml-6 mt-2 space-y-1">
              <li>
                <strong>Account information:</strong> Name, email address, and
                password (hashed).
              </li>
              <li>
                <strong>Profile information:</strong> Bio, district
                affiliation, and professional role.
              </li>
              <li>
                <strong>District data:</strong> Publicly available aggregate
                data from the NCES Common Core of Data (enrollment,
                demographics, locale type).
              </li>
              <li>
                <strong>Consent records:</strong> Timestamp and IP address of
                privacy agreement acceptance.
              </li>
            </ul>
          </section>

          <section>
            <h2 className="font-display text-abyss text-lg font-bold mb-2">
              3. How We Use Your Information
            </h2>
            <p>Your information is used solely to:</p>
            <ul className="list-disc ml-6 mt-2 space-y-1">
              <li>
                Facilitate professional community matching among K-12 literacy
                educators.
              </li>
              <li>Display your profile to other authenticated users.</li>
              <li>Send transactional emails (verification, password reset).</li>
              <li>Improve platform functionality and user experience.</li>
            </ul>
          </section>

          <section>
            <h2 className="font-display text-abyss text-lg font-bold mb-2">
              4. FERPA Compliance
            </h2>
            <p>
              TRIBUTARY does not store, transmit, or process student education
              records. All district-level data displayed on the platform is
              sourced from publicly available NCES datasets. No individual
              student information is collected or accessible through this
              platform.
            </p>
          </section>

          <section>
            <h2 className="font-display text-abyss text-lg font-bold mb-2">
              5. Data Sharing
            </h2>
            <p>
              We do not sell, rent, or share your personal information with
              third parties for marketing purposes. Your data may be shared
              only with:
            </p>
            <ul className="list-disc ml-6 mt-2 space-y-1">
              <li>
                Other authenticated users (limited profile information as
                described in Section 2).
              </li>
              <li>
                Service providers necessary for platform operation (hosting,
                email delivery) under strict data processing agreements.
              </li>
              <li>Law enforcement when required by law.</li>
            </ul>
          </section>

          <section>
            <h2 className="font-display text-abyss text-lg font-bold mb-2">
              6. Data Security
            </h2>
            <p>
              We implement industry-standard security measures including
              encrypted connections (TLS), hashed passwords, JWT-based
              authentication with token rotation, and regular security audits.
            </p>
          </section>

          <section>
            <h2 className="font-display text-abyss text-lg font-bold mb-2">
              7. Your Rights
            </h2>
            <p>
              You have the right to access, correct, or request deletion of
              your personal data at any time. Account deactivation is performed
              via soft delete to maintain data integrity. Contact
              support@upstreamliteracy.org for data requests.
            </p>
          </section>

          <section>
            <h2 className="font-display text-abyss text-lg font-bold mb-2">
              8. Contact
            </h2>
            <p>
              For questions about this privacy policy, contact Upstream
              Literacy at privacy@upstreamliteracy.org.
            </p>
          </section>

          <p className="text-stone text-xs pt-4 border-t border-pebble">
            Last updated: March 2026 &middot; Version 1.0
          </p>
        </div>
      </div>
    </div>
  );
}
